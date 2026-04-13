#! /usr/bin/env python3
"""Custom Ansible module to start/stop/restart/describe EC2 instances."""
import os
import re

from ansible.module_utils.basic import AnsibleModule


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
INSTANCE_ID_RE = re.compile(r'^i-[0-9a-f]{8,17}$')
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

    _get_region(module)  # validates region availability; raises via fail_json otherwise

    # Stub: actual dispatch added in later tasks.
    module.exit_json(
        changed=False,
        state=params['state'],
        instances=[],
        skipped_instance_ids=[],
        diff={'before': {'states': {}}, 'after': {'states': {}}},
    )


if __name__ == '__main__':
    main()
