#!/usr/bin/env python3

import boto3
import time
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: ec2_instance_control
short_description: Stop and start EC2 instances
description:
    - Stop and start EC2 instances with proper state verification
    - Uses boto3 to interact with AWS EC2 API
    - Handles waiting for state transitions
version_added: "1.0.0"
options:
    instance_id:
        description: EC2 instance ID to control
        required: true
        type: str
    region:
        description: AWS region
        required: false
        default: us-east-1
        type: str
    action:
        description: Action to perform
        required: true
        choices: ['stop', 'start', 'restart', 'describe']
        type: str
    wait_timeout:
        description: Maximum time to wait for state change (seconds)
        required: false
        default: 300
        type: int
author:
    - CommCare Cloud Team
"""

EXAMPLES = """
- name: Stop EC2 instance
  ec2_instance_control:
    instance_id: i-1234567890abcdef0
    region: us-east-1
    action: stop

- name: Start EC2 instance
  ec2_instance_control:
    instance_id: i-1234567890abcdef0
    region: us-east-1
    action: start

- name: Restart EC2 instance (stop then start)
  ec2_instance_control:
    instance_id: i-1234567890abcdef0
    region: us-east-1
    action: restart
"""

RETURN = """
instance_id:
    description: The EC2 instance ID
    type: str
    returned: always
state:
    description: Current state of the instance
    type: str
    returned: always
previous_state:
    description: Previous state of the instance (for restart action)
    type: str
    returned: when action is restart
changed:
    description: Whether the instance state was changed
    type: bool
    returned: always
"""


def get_instance_state(ec2_client, instance_id):
    """Get current state of EC2 instance"""
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        return instance['State']['Name']
    except Exception as e:
        raise Exception(f"Failed to describe instance {instance_id}: {str(e)}")


def wait_for_state(ec2_client, instance_id, target_state, timeout=300):
    """Wait for instance to reach target state"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_state = get_instance_state(ec2_client, instance_id)
        if current_state == target_state:
            return True
        time.sleep(5)
    return False


def stop_instance(ec2_client, instance_id, wait_timeout):
    """Stop EC2 instance"""
    current_state = get_instance_state(ec2_client, instance_id)
    
    if current_state == 'stopped':
        return {'changed': False, 'state': 'stopped', 'message': 'Instance already stopped'}
    
    if current_state != 'running':
        raise Exception(f"Cannot stop instance in state: {current_state}")
    
    # Stop the instance
    ec2_client.stop_instances(InstanceIds=[instance_id])
    
    # Wait for stopped state
    if not wait_for_state(ec2_client, instance_id, 'stopped', wait_timeout):
        raise Exception(f"Instance {instance_id} did not stop within {wait_timeout} seconds")
    
    return {'changed': True, 'state': 'stopped', 'message': 'Instance stopped successfully'}


def start_instance(ec2_client, instance_id, wait_timeout):
    """Start EC2 instance"""
    current_state = get_instance_state(ec2_client, instance_id)
    
    if current_state == 'running':
        return {'changed': False, 'state': 'running', 'message': 'Instance already running'}
    
    if current_state != 'stopped':
        raise Exception(f"Cannot start instance in state: {current_state}")
    
    # Start the instance
    ec2_client.start_instances(InstanceIds=[instance_id])
    
    # Wait for running state
    if not wait_for_state(ec2_client, instance_id, 'running', wait_timeout):
        raise Exception(f"Instance {instance_id} did not start within {wait_timeout} seconds")
    
    return {'changed': True, 'state': 'running', 'message': 'Instance started successfully'}


def restart_instance(ec2_client, instance_id, wait_timeout):
    """Restart EC2 instance (stop then start)"""
    initial_state = get_instance_state(ec2_client, instance_id)
    
    # Stop the instance
    stop_result = stop_instance(ec2_client, instance_id, wait_timeout)
    
    # Start the instance
    start_result = start_instance(ec2_client, instance_id, wait_timeout)
    
    return {
        'changed': stop_result['changed'] or start_result['changed'],
        'state': 'running',
        'previous_state': initial_state,
        'message': 'Instance restarted successfully'
    }


def describe_instance(ec2_client, instance_id):
    """Get instance state"""
    state = get_instance_state(ec2_client, instance_id)
    return {'changed': False, 'state': state, 'message': f'Instance state: {state}'}


def main():
    module_args = dict(
        instance_id=dict(type='str', required=True),
        region=dict(type='str', required=False, default='us-east-1'),
        action=dict(type='str', required=True, choices=['stop', 'start', 'restart', 'describe']),
        wait_timeout=dict(type='int', required=False, default=300)
    )

    result = dict(
        changed=False,
        instance_id='',
        state='',
        message=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    instance_id = module.params['instance_id']
    region = module.params['region']
    action = module.params['action']
    wait_timeout = module.params['wait_timeout']

    try:
        # Create EC2 client (uses IAM role credentials automatically)
        ec2_client = boto3.client('ec2', region_name=region)
        
        # Perform the requested action
        if action == 'stop':
            action_result = stop_instance(ec2_client, instance_id, wait_timeout)
        elif action == 'start':
            action_result = start_instance(ec2_client, instance_id, wait_timeout)
        elif action == 'restart':
            action_result = restart_instance(ec2_client, instance_id, wait_timeout)
        elif action == 'describe':
            action_result = describe_instance(ec2_client, instance_id)
        
        # Update result
        result.update(action_result)
        result['instance_id'] = instance_id
        
        module.exit_json(**result)
        
    except Exception as e:
        module.fail_json(msg=str(e), **result)


if __name__ == '__main__':
    main()
