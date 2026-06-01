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
    - Designed to run with delegate_to localhost. AWS credentials and the target region are picked up from the standard boto3 credential chain; in the commcare-cloud workflow the AWS_PROFILE and AWS_REGION environment variables are exported automatically before ansible runs.

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
        'command': {'type': 'str', 'required': True, 'choices': [c.value for c in InstanceCommand]},
        'region': {'type': 'str', 'required': False, 'default': None},
        'wait': {'type': 'bool', 'required': False, 'default': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    instance_ids = params['instance_ids']
    if not instance_ids:
        module.fail_json(msg="'instance_ids' must be a non-empty list.")

    bad = [i for i in instance_ids if not INSTANCE_ID_RE.match(i)]
    if bad:
        module.fail_json(msg=f"Malformed instance IDs: {bad!r}")

    region = _get_region(module)

    try:
        client = _get_ec2_client(region)
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    module.exit_json()


if __name__ == '__main__':
    main()
