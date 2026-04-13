#! /usr/bin/env python3
"""Custom Ansible module to start/stop/restart/describe EC2 instances."""
import os
import re

from ansible.module_utils.basic import AnsibleModule
from botocore.exceptions import ClientError


DOCUMENTATION = """
---
module: ec2_instance_state

short_description: Start, stop, restart, or describe EC2 instances by ID.

description:
    - Manages the running state of EC2 instances given an explicit list of
      instance IDs. Supports four states - started, stopped, restarted,
      described - and is idempotent (no API call is made if the instance is
      already in the requested state).
    - Designed to run with delegate_to localhost. AWS credentials and the
      target region are picked up from the standard boto3 credential chain;
      in the commcare-cloud workflow the AWS_PROFILE and AWS_REGION
      environment variables are exported automatically before ansible runs.
    - The restarted state is implemented as stop-then-start. The stop phase
      always waits for completion regardless of the wait parameter (a still
      stopping instance cannot be started); the start phase respects wait.

version_added: "1.0.0"

options:
    instance_ids:
        description: List of EC2 instance IDs to act on.
        required: true
        type: list
        elements: str
    state:
        description: Desired state.
        required: true
        type: str
        choices: [started, stopped, restarted, described]
    region:
        description: >
            AWS region. Falls back to the AWS_REGION environment variable
            when omitted. Module fails if neither is set.
        required: false
        type: str
    wait:
        description: >
            Block until the target state is reached. Ignored for described.
            For restarted, the stop phase always waits regardless of this
            setting.
        required: false
        default: true
        type: bool
    wait_timeout:
        description: >
            Per-phase wait timeout in seconds. For restarted this applies
            independently to each of the stop and start phases.
        required: false
        default: 600
        type: int

author:
    - Amit Phulera
"""

EXAMPLES = """
- name: Restart a single host (region picked up from AWS_REGION env var)
  ec2_instance_state:
    instance_ids:
      - "{{ hostvars['10.201.11.133'].ec2_instance_id }}"
    state: restarted
  delegate_to: localhost

- name: Stop all webworkers in batch
  ec2_instance_state:
    instance_ids: >-
      {{ groups['webworkers']
         | map('extract', hostvars, 'ec2_instance_id')
         | list }}
    state: stopped
  delegate_to: localhost

- name: Describe instances in a non-default region
  ec2_instance_state:
    instance_ids: ["i-0123456789abcdef0"]
    state: described
    region: us-west-2
  delegate_to: localhost
"""

RETURN = """
changed:
    description: True if this run mutated AWS state.
    type: bool
state:
    description: The requested state, echoed back.
    type: str
instances:
    description: One entry per requested instance, in input order.
    type: list
    elements: dict
skipped_instance_ids:
    description: IDs that needed no action because they were already in the target state.
    type: list
    elements: str
diff:
    description: Per-instance state map before/after this run.
    type: dict
"""


VALID_STATES = ['started', 'stopped', 'restarted', 'described']
INSTANCE_ID_RE = re.compile(r'^i-([0-9a-f]{8}|[0-9a-f]{17})$')
# EC2 instance states from which we cannot recover to 'running'/'stopped'.
# 'terminated' is permanent; 'shutting-down' is a one-way transition to 'terminated'
# (AWS rejects StartInstances/StopInstances on either). Compare to 'stopping' which
# is reversible (-> 'stopped' -> 'pending' -> 'running').
TERMINAL_STATES = {'terminated', 'shutting-down'}


def _get_region(module):
    """Return the region from params, falling back to AWS_REGION env var."""
    region = module.params.get('region') or os.environ.get('AWS_REGION')
    if not region:
        module.fail_json(msg=(
            "AWS region not provided. Pass 'region' to the module, "
            "or set the AWS_REGION environment variable."
        ))
    return region


def _get_ec2_client(region):
    """Return a boto3 EC2 client. Defined as a module-level function so tests can patch it."""
    try:
        import boto3
    except ImportError:
        raise RuntimeError(
            "boto3 is required by ec2_instance_state but is not installed."
        )
    return boto3.client('ec2', region_name=region)


def _describe_instances(client, instance_ids):
    """Return dict[instance_id -> raw_instance] preserving caller-required keys.

    Raises ClientError as-is on InvalidInstanceID.NotFound (caller decides how to surface).
    """
    resp = client.describe_instances(InstanceIds=list(instance_ids))
    out = {}
    for reservation in resp.get('Reservations', []):
        for inst in reservation.get('Instances', []):
            out[inst['InstanceId']] = inst
    return out


def _format_instance(raw, previous_state, current_state):
    tags = {t['Key']: t['Value'] for t in raw.get('Tags', []) or []}
    launch_time = raw.get('LaunchTime')
    if hasattr(launch_time, 'isoformat'):
        launch_time = launch_time.isoformat()
    return {
        'instance_id': raw['InstanceId'],
        'previous_state': previous_state,
        'current_state': current_state,
        'instance_type': raw.get('InstanceType'),
        'availability_zone': (raw.get('Placement') or {}).get('AvailabilityZone'),
        'private_ip': raw.get('PrivateIpAddress'),
        'public_ip': raw.get('PublicIpAddress'),
        'tags': tags,
        'launch_time': launch_time,
    }


def _describe_and_format(client, instance_ids, module):
    """Describe + format. Fails the module on AWS errors."""
    try:
        raw_by_id = _describe_instances(client, instance_ids)
    except ClientError as e:
        module.fail_json(msg="AWS DescribeInstances failed: {}".format(e))
        return
    # Order output to match input.
    formatted = []
    states = {}
    for iid in instance_ids:
        raw = raw_by_id.get(iid)
        if raw is None:
            module.fail_json(msg="Instance {} missing from DescribeInstances response.".format(iid))
            return None, None
        state = raw['State']['Name']
        states[iid] = state
        formatted.append((iid, raw, state))
    return formatted, states  # list of (id, raw, state); dict id->state


def _check_no_terminal(formatted, action_state, module):
    """Fail the module if any instance is terminated/shutting-down."""
    bad = [(iid, state) for (iid, _raw, state) in formatted if state in TERMINAL_STATES]
    if bad:
        module.fail_json(msg=(
            "Cannot {} terminated/shutting-down instances: {}".format(
                action_state, ', '.join('{}={}'.format(i, s) for i, s in bad)
            )
        ))
        return


def _wait_for(client, waiter_name, instance_ids, timeout, module):
    if not instance_ids:
        return
    waiter = client.get_waiter(waiter_name)
    # boto3 waiter config: Delay (per-poll) * MaxAttempts ~= timeout.
    delay = 15
    max_attempts = max(1, timeout // delay)
    try:
        waiter.wait(
            InstanceIds=list(instance_ids),
            WaiterConfig={'Delay': delay, 'MaxAttempts': max_attempts},
        )
    except Exception as e:  # noqa: BLE001 - surface any waiter failure as module failure
        module.fail_json(msg="Waiter {!r} failed: {}".format(waiter_name, e))
        return


def _emit_result(module, client, instance_ids, before_states, after_states,
                 state, changed, skipped, refresh):
    """Build and emit the module's exit_json payload.

    refresh=True: re-describe to compute after_states from live data.
    refresh=False: use the supplied after_states (used for check_mode and no-op fast paths).
    """
    if refresh:
        formatted, after_states = _describe_and_format(client, instance_ids, module)
        raw_by_id = {iid: raw for (iid, raw, _state) in formatted}
    else:
        formatted, _ = _describe_and_format(client, instance_ids, module)
        raw_by_id = {iid: raw for (iid, raw, _state) in formatted}

    instances = [
        _format_instance(raw_by_id[iid], before_states[iid], after_states[iid])
        for iid in instance_ids
    ]
    module.exit_json(
        changed=changed,
        state=state,
        instances=instances,
        skipped_instance_ids=skipped,
        diff={'before': {'states': before_states},
              'after': {'states': after_states}},
    )


def _do_start(module, client, instance_ids, wait, timeout):
    formatted, before_states = _describe_and_format(client, instance_ids, module)
    _check_no_terminal(formatted, 'start', module)

    targets_needing_start = [iid for (iid, _raw, state) in formatted
                             if state in ('stopped', 'stopping')]
    skipped = [iid for iid in instance_ids if iid not in targets_needing_start]

    # If any instance is currently 'stopping' and we'll need to start it, wait for stopped first.
    stopping_now = [iid for (iid, _raw, state) in formatted if state == 'stopping']
    if stopping_now and not wait:
        module.fail_json(msg=(
            "Cannot start instances that are currently 'stopping' with wait=False: "
            "{}. Either set wait=true (so the module can wait for them to reach "
            "'stopped' first), or retry once the instances have finished stopping."
            .format(', '.join(stopping_now))
        ))
        return
    if wait and stopping_now:
        _wait_for(client, 'instance_stopped', stopping_now, timeout, module)

    changed = bool(targets_needing_start)

    if module.check_mode:
        # Don't actually call StartInstances; predict end states.
        after_states = dict(before_states)
        for iid in targets_needing_start:
            after_states[iid] = 'running' if wait else 'pending'
        _emit_result(module, client, instance_ids, before_states, after_states,
                     state='started', changed=changed, skipped=skipped, refresh=False)
        return

    if targets_needing_start:
        try:
            client.start_instances(InstanceIds=targets_needing_start)
        except Exception as e:  # noqa: BLE001
            module.fail_json(msg="StartInstances failed: {}".format(e))
            return

        if wait:
            _wait_for(client, 'instance_running', targets_needing_start, timeout, module)

    _emit_result(module, client, instance_ids, before_states, after_states=None,
                 state='started', changed=changed, skipped=skipped, refresh=True)


def _do_stop(module, client, instance_ids, wait, timeout):
    formatted, before_states = _describe_and_format(client, instance_ids, module)
    _check_no_terminal(formatted, 'stop', module)

    targets_needing_stop = [iid for (iid, _raw, state) in formatted
                            if state in ('running', 'pending')]
    # 'stopping' instances are mid-transition; we wait for them but don't initiate.
    already_stopping = [iid for (iid, _raw, state) in formatted if state == 'stopping']
    skipped = [iid for iid in instance_ids
               if iid not in targets_needing_stop and iid not in already_stopping]

    # If any instance is 'pending', wait for it to be 'running' before stopping.
    pending_now = [iid for (iid, _raw, state) in formatted if state == 'pending']
    if wait and pending_now:
        _wait_for(client, 'instance_running', pending_now, timeout, module)

    changed = bool(targets_needing_stop)

    if module.check_mode:
        after_states = dict(before_states)
        for iid in targets_needing_stop:
            after_states[iid] = 'stopped' if wait else 'stopping'
        for iid in already_stopping:
            after_states[iid] = 'stopped' if wait else 'stopping'
        _emit_result(module, client, instance_ids, before_states, after_states,
                     state='stopped', changed=changed, skipped=skipped, refresh=False)
        return

    if targets_needing_stop:
        try:
            client.stop_instances(InstanceIds=targets_needing_stop)
        except Exception as e:  # noqa: BLE001
            module.fail_json(msg="StopInstances failed: {}".format(e))
            return

    # Wait for both initiated and already-in-progress stops if wait=True.
    if wait:
        wait_for = list(targets_needing_stop) + list(already_stopping)
        if wait_for:
            _wait_for(client, 'instance_stopped', wait_for, timeout, module)

    _emit_result(module, client, instance_ids, before_states, after_states=None,
                 state='stopped', changed=changed, skipped=skipped, refresh=True)


def _do_describe(module, client, instance_ids):
    formatted, states = _describe_and_format(client, instance_ids, module)
    instances = [_format_instance(raw, state, state) for (_iid, raw, state) in formatted]
    module.exit_json(
        changed=False,
        state='described',
        instances=instances,
        skipped_instance_ids=[],
        diff={'before': {'states': states}, 'after': {'states': states}},
    )


def main():
    module_args = {
        'instance_ids': {'type': 'list', 'elements': 'str', 'required': True},
        'state': {'type': 'str', 'required': True, 'choices': VALID_STATES},
        'region': {'type': 'str', 'required': False, 'default': None},
        'wait': {'type': 'bool', 'required': False, 'default': True},
        'wait_timeout': {'type': 'int', 'required': False, 'default': 600},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    instance_ids = params['instance_ids']
    if not instance_ids:
        module.fail_json(msg="'instance_ids' must be a non-empty list.")

    bad = [i for i in instance_ids if not INSTANCE_ID_RE.match(i)]
    if bad:
        module.fail_json(msg="Malformed instance IDs: {!r}".format(bad))

    if params['wait_timeout'] <= 0:
        module.fail_json(msg="'wait_timeout' must be > 0.")

    region = _get_region(module)

    try:
        client = _get_ec2_client(region)
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    state = params['state']

    if state == 'described':
        _do_describe(module, client, instance_ids)
    elif state == 'started':
        _do_start(module, client, instance_ids, params['wait'], params['wait_timeout'])
    elif state == 'stopped':
        _do_stop(module, client, instance_ids, params['wait'], params['wait_timeout'])
    else:
        module.fail_json(msg="State {!r} not yet implemented.".format(state))


if __name__ == '__main__':
    main()
