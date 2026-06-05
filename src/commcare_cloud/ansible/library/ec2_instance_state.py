#! /usr/bin/env python3
"""Custom Ansible module to start/stop/stop_and_start/describe EC2 instances."""
import os
import re
from enum import Enum

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: ec2_instance_state

short_description: Start, stop, stop_and_start, or describe EC2 instances by ID.

description:
    - Manages the running state of EC2 instances given an explicit list of
      instance IDs. Supports four commands - describe, start, stop, stop_and_start,
      and is idempotent (no API call is made if the instance is already in the requested state).
    - Designed to run with delegate_to localhost. AWS credentials and the target
      region are picked up from the standard boto3 credential chain; in the
      commcare-cloud workflow the AWS_PROFILE and AWS_REGION environment variables
      are exported automatically before ansible runs.

version_added: "1.0.0"

options:
    instance_ids:
        description: List of EC2 instance IDs to act on.
        required: true
        type: list
        elements: str
    command:
        description: Command to execute.
        required: true
        type: str
        choices: [describe, start, stop, stop_and_start]
    region:
        description: >
            AWS region. Falls back to the AWS_REGION environment variable
            when omitted. Module fails if neither is set.
        required: false
        type: str
    wait:
        description: >
            Block until the final target state (running/stopped) is reached.
            Ignored for describe. Transition preconditions are always waited
            for regardless of this setting: a 'stopping' instance is awaited to
            'stopped' before it is started, and a 'pending' instance is awaited
            to 'running' before it is stopped. For stop_and_start the stop
            phase always waits; this setting governs only the final start phase.
        required: false
        default: true
        type: bool

author:
    - Amit Phulera
"""

EXAMPLES = """
- name: Stop and start a single host (region picked up from AWS_REGION env var)
  ec2_instance_state:
    instance_ids:
      - "{{ hostvars['10.201.11.133'].ec2_instance_id }}"
    command: stop_and_start
  delegate_to: localhost

- name: Stop all webworkers in batch
  ec2_instance_state:
    instance_ids: >-
      {{ groups['webworkers']
         | map('extract', hostvars, 'ec2_instance_id')
         | list }}
    command: stop
  delegate_to: localhost

- name: Describe instances in a non-default region
  ec2_instance_state:
    instance_ids: ["i-0123456789abcdef0"]
    command: describe
    region: us-west-2
  delegate_to: localhost
"""

RETURN = """
changed:
    description: True if this run mutated AWS state.
    type: bool
command:
    description: The requested command, echoed back.
    type: str
instances:
    description: One entry per requested instance, in input order.
    type: list
    elements: dict
unchanged_instance_ids:
    description: IDs that needed no action because they were already in the target state.
    type: list
    elements: str
diff:
    description: Per-instance state map before/after this run.
    type: dict
"""


class InstanceCommand(str, Enum):
    DESCRIBE = 'describe'
    START = 'start'
    STOP = 'stop'
    STOP_AND_START = 'stop_and_start'


INSTANCE_ID_RE = re.compile(r'^i-([0-9a-f]{8}|[0-9a-f]{17})$')


# EC2 instance lifecycle states as returned by DescribeInstances (State.Name).
class InstanceState(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    SHUTTING_DOWN = 'shutting-down'
    TERMINATED = 'terminated'


TERMINATED_STATES = {InstanceState.TERMINATED, InstanceState.SHUTTING_DOWN}


def _get_region(module):
    """Return the region from params, falling back to AWS_REGION env var."""
    region = module.params.get('region') or os.environ.get('AWS_REGION')
    if not region:
        module.fail_json(msg=(
            "AWS region not provided. Pass 'region' to the module, "
            "or set the AWS_REGION environment variable."
        ))
    return region


def _get_ec2_client(module, region):
    """Return a boto3 EC2 client. Defined as a module-level function so tests can patch it."""
    try:
        import boto3
    except ImportError:
        module.fail_json(msg="boto3 is required by ec2_instance_state but is not installed.")
    return boto3.client('ec2', region_name=region)


class Instance:

    def __init__(self, instance_id, raw):
        self.instance_id = instance_id
        self.raw = raw
        self.previous_state = self.state
        self.current_state = self.state

    @property
    def state(self):
        return self.raw['State']['Name']

    @property
    def is_terminated(self):
        return self.state in TERMINATED_STATES

    @property
    def name(self):
        """The 'Name' tag value, if the instance has one. Otherwise return the private IP address."""
        for tag in self.raw.get('Tags', []):
            if tag['Key'] == 'Name':
                return tag['Value']
        return self.raw.get('PrivateIpAddress')

    @property
    def label(self):
        """Human-friendly identifier for error messages."""
        return f"{self.name} ({self.instance_id})"

    @property
    def can_start(self):
        return self.state in (InstanceState.STOPPED, InstanceState.STOPPING)

    @property
    def can_stop(self):
        return self.state in (InstanceState.RUNNING, InstanceState.PENDING)

    def to_result(self):
        tags = {t['Key']: t['Value'] for t in self.raw.get('Tags', []) or []}
        launch_time = self.raw.get('LaunchTime')
        if hasattr(launch_time, 'isoformat'):
            launch_time = launch_time.isoformat()
        return {
            'instance_id': self.instance_id,
            'previous_state': self.previous_state,
            'current_state': self.current_state,
            'name': self.name,
            'instance_type': self.raw.get('InstanceType'),
            'availability_zone': (self.raw.get('Placement') or {}).get('AvailabilityZone'),
            'private_ip': self.raw.get('PrivateIpAddress'),
            'public_ip': self.raw.get('PublicIpAddress'),
            'tags': tags,
            'launch_time': launch_time,
        }


def _build_payload(instances, command, changed, unchanged_instance_ids):
    members = list(instances.values())
    return {
        'changed': changed,
        'command': command,
        'instances': [m.to_result() for m in members],
        'unchanged_instance_ids': unchanged_instance_ids,
        'diff': {
            'before': {'states': {m.instance_id: m.previous_state for m in members}},
            'after': {'states': {m.instance_id: m.current_state for m in members}},
        },
    }


class EC2InstanceManager:

    def __init__(self, client, module):
        self.client = client
        self.module = module

    def describe(self, instance_ids):
        instances = self._describe_instances(instance_ids)
        return _build_payload(instances, InstanceCommand.DESCRIBE, changed=False,
                              unchanged_instance_ids=[])

    def _describe_instances(self, instance_ids):
        """Return OrderedDict[id -> Instance] in input order.

        Fails the module on AWS errors
        """
        from botocore.exceptions import ClientError
        try:
            resp = self.client.describe_instances(InstanceIds=list(instance_ids))
        except ClientError as e:
            self.module.fail_json(msg=f"AWS DescribeInstances failed: {e}")
            return
        by_id = {}
        for reservation in resp.get('Reservations', []):
            for raw in reservation.get('Instances', []):
                by_id[raw['InstanceId']] = Instance(raw['InstanceId'], raw)

        # Reservations are not returned in the order of the requested ids, so
        # rebuild the map in input order to honor the documented contract.
        return {iid: by_id[iid] for iid in instance_ids}

    def start(self, instance_ids, wait):
        instances = self._describe_instances(instance_ids)
        self._check_not_terminated(instances)

        targets = [iid for iid, inst in instances.items() if inst.can_start]
        unchanged = [iid for iid, inst in instances.items() if not inst.can_start]
        changed = bool(targets)

        if self.module.check_mode:
            # Predict end states; never wait, never call StartInstances.
            for iid in targets:
                instances[iid].current_state = InstanceState.RUNNING
            return _build_payload(instances, InstanceCommand.START, changed, unchanged)

        if not targets:
            return _build_payload(instances, InstanceCommand.START, False, unchanged)

        before_states = {iid: inst.state for iid, inst in instances.items()}

        # Precondition (always, regardless of `wait`): a 'stopping' instance must
        # reach 'stopped' before StartInstances will accept it.
        stopping = [instances[iid] for iid in targets if instances[iid].state == InstanceState.STOPPING]
        self._wait_for('instance_stopped', stopping)

        try:
            self.client.start_instances(InstanceIds=targets)
        except Exception as e:  # noqa: BLE001
            labels = self._labels(instances[iid] for iid in targets)
            self.module.fail_json(msg=f"StartInstances failed for {labels}: {e}")
            return

        if wait:
            self._wait_for('instance_running', [instances[iid] for iid in targets])
            instances = self._describe_instances(instance_ids)
            for iid, inst in instances.items():
                inst.previous_state = before_states[iid]
        else:
            for iid in targets:
                instances[iid].current_state = InstanceState.PENDING

        return _build_payload(instances, InstanceCommand.START, changed, unchanged)

    def stop(self, instance_ids, wait):
        instances = self._describe_instances(instance_ids)
        self._check_not_terminated(instances)

        targets = [iid for iid, inst in instances.items() if inst.can_stop]
        # 'stopping' instances are mid-transition: we wait for them but don't initiate.
        already_stopping = [iid for iid, inst in instances.items()
                            if inst.state == InstanceState.STOPPING]
        wait_for_stopped = targets + already_stopping
        unchanged = [iid for iid in instance_ids
                     if iid not in targets and iid not in already_stopping]
        changed = bool(targets)

        if self.module.check_mode:
            for iid in wait_for_stopped:
                instances[iid].current_state = InstanceState.STOPPED
            return _build_payload(instances, InstanceCommand.STOP, changed, unchanged)

        if not wait_for_stopped:
            return _build_payload(instances, InstanceCommand.STOP, False, unchanged)

        before_states = {iid: inst.state for iid, inst in instances.items()}

        # Precondition (always, regardless of `wait`): a 'pending' instance must
        # reach 'running' before it can be deterministically stopped.
        pending = [instances[iid] for iid in targets if instances[iid].state == InstanceState.PENDING]
        self._wait_for('instance_running', pending)

        if targets:
            try:
                self.client.stop_instances(InstanceIds=targets)
            except Exception as e:  # noqa: BLE001
                labels = self._labels(instances[iid] for iid in targets)
                self.module.fail_json(msg=f"StopInstances failed for {labels}: {e}")
                return

        if wait:
            self._wait_for('instance_stopped', [instances[iid] for iid in wait_for_stopped])
            instances = self._describe_instances(instance_ids)
            for iid, inst in instances.items():
                inst.previous_state = before_states[iid]
        else:
            for iid in wait_for_stopped:
                instances[iid].current_state = InstanceState.STOPPING

        return _build_payload(instances, InstanceCommand.STOP, changed, unchanged)

    def stop_and_start(self, instance_ids, wait):
        stop_payload = self.stop(instance_ids, wait=True)

        # Honor the user's `wait` choice for the final running wait.
        start_payload = self.start(instance_ids, wait=wait)

        before_states = stop_payload['diff']['before']['states']
        after_states = start_payload['diff']['after']['states']

        instances = []
        for inst in start_payload['instances']:
            merged = dict(inst)
            merged['previous_state'] = before_states[inst['instance_id']]
            instances.append(merged)

        # A successful stop_and_start always restarts every non-terminal instance:
        # the stop phase leaves them all stopped, so the start phase must report a
        # change. In check mode nothing is actually stopped, so the start phase sees
        # the original running instances and reports no change — skip the invariant
        # check there.
        changed = True
        if not self.module.check_mode and not start_payload['changed']:
            self.module.fail_json(
                msg="stop_and_start invariant violated: start phase reported no "
                    "change after a completed stop phase.",
                start_payload=start_payload)

        # unchanged = ids that were no-ops in BOTH phases.
        # Highly unlikely to happen in practice, but we sort to make the result deterministic.
        unchanged = sorted(set(stop_payload['unchanged_instance_ids'])
                           & set(start_payload['unchanged_instance_ids']))

        return {
            'changed': changed,
            'command': InstanceCommand.STOP_AND_START,
            'instances': instances,
            'unchanged_instance_ids': unchanged,
            'diff': {'before': {'states': before_states},
                     'after': {'states': after_states}},
        }

    def _check_not_terminated(self, instances):
        """Fail the module if any instance is terminated/shutting-down."""
        bad = [i for i in instances.values() if i.is_terminated]
        if bad:
            bad_instances = ', '.join(f'{i.label}={i.state}' for i in bad)
            self.module.fail_json(
                msg=f"Cannot {self.module.params['command']} terminated/shutting-down instances: {bad_instances}")

    def _wait_for(self, waiter_name, instances):
        if not instances or self.module.check_mode:
            return
        waiter = self.client.get_waiter(waiter_name)
        try:
            waiter.wait(InstanceIds=[i.instance_id for i in instances])
        except Exception as e:  # noqa: BLE001 - surface any waiter failure as module failure
            self.module.fail_json(
                msg=f"Waiter {waiter_name!r} failed for {self._labels(instances)}: {e}")
            return

    def _labels(self, instances):
        return ', '.join(i.label for i in instances)


def main():
    module_args = {
        'instance_ids': {'type': 'list', 'elements': 'str', 'required': True},
        'command': {'type': 'str', 'required': True, 'choices': [c.value for c in InstanceCommand]},
        'region': {'type': 'str', 'required': False, 'default': None},
        'wait': {'type': 'bool', 'required': False, 'default': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    instance_ids = params['instance_ids']
    if not instance_ids:
        module.fail_json(msg="'instance_ids' must be a non-empty list.")

    bad_ids = [i for i in instance_ids if not INSTANCE_ID_RE.match(i)]
    if bad_ids:
        module.fail_json(msg=f"Malformed instance IDs: {bad_ids!r}")

    region = _get_region(module)

    client = _get_ec2_client(module, region)

    manager = EC2InstanceManager(client, module)

    command = params['command']

    if command == InstanceCommand.DESCRIBE:
        payload = manager.describe(instance_ids)
    elif command == InstanceCommand.START:
        payload = manager.start(instance_ids, params['wait'])
    elif command == InstanceCommand.STOP:
        payload = manager.stop(instance_ids, params['wait'])
    elif command == InstanceCommand.STOP_AND_START:
        payload = manager.stop_and_start(instance_ids, params['wait'])
    else:
        module.fail_json(msg=f"Unknown command {command!r}.")
        return

    module.exit_json(**payload)


if __name__ == '__main__':
    main()
