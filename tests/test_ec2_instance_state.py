# Add the library directory to sys.path so we can import the module by name.
# We must also ensure that the tests/ directory does NOT appear before the
# library dir on sys.path, because tests/ansible.py would otherwise shadow
# the real `ansible` package when ec2_instance_state does
# `from ansible.module_utils.basic import AnsibleModule`.
import os
import sys
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from . import ansible

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
LIBRARY_DIR = os.path.abspath(os.path.join(
    TESTS_DIR, '..', 'src', 'commcare_cloud', 'ansible', 'library'
))
# Remove any existing entry for the tests/ directory from sys.path so that
# tests/ansible.py cannot shadow the real ansible package.
sys.path = [p for p in sys.path if os.path.abspath(p) != TESTS_DIR]
sys.path.insert(0, LIBRARY_DIR)

import ec2_instance_state  # noqa: E402


def run_module(args, fake_client=None):
    """
    Invoke ec2_instance_state.main() with the given args dict.

    Returns ``{'failed': bool, 'result': <exit/fail kwargs>}``. Arg encoding,
    exit/fail handling, and warning capture are delegated to tests.ansible.
    """
    client_patch = (
        patch.object(ec2_instance_state, '_get_ec2_client', return_value=fake_client)
        if fake_client is not None else nullcontext()
    )
    with client_patch:
        try:
            result = ansible.run(ec2_instance_state, dict(args))
            return {'failed': False, 'result': result}
        except ansible.Fail as e:
            return {'failed': True, 'result': e.args[1]}


class TestArgumentValidation(unittest.TestCase):

    def setUp(self):
        # Ensure AWS_REGION is unset by default; individual tests set it as needed.
        self._orig_region = os.environ.pop('AWS_REGION', None)

    def tearDown(self):
        if self._orig_region is not None:
            os.environ['AWS_REGION'] = self._orig_region

    def test_missing_region_fails(self):
        result = run_module({
            'instance_ids': ['i-0123456789abcdef0'],
            'command': 'describe',
        })
        assert result['failed']
        expected_msg = "AWS region not provided. Pass 'region' to the module, or set the AWS_REGION environment variable."
        assert result['result']['msg'] == expected_msg, f"Expected {expected_msg} but got {result['result']['msg']}"

    def test_invalid_command_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': ['i-0123456789abcdef0'],
            'command': 'bogus',
        })
        assert result['failed']
        expected_msg = "value of command must be one of: describe, start, stop, stop_and_start, got: bogus"
        assert result['result']['msg'] == expected_msg, "Expected {expected_msg} but got {result_msg}".format(expected_msg=expected_msg, result_msg=result['result']['msg'])

    def test_empty_instance_ids_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': [],
            'command': 'describe',
        })
        expected_msg = "'instance_ids' must be a non-empty list."
        assert result['failed']
        assert result['result']['msg'] == expected_msg, "Expected {expected_msg} but got {result_msg}".format(expected_msg=expected_msg, result_msg=result['result']['msg'])

    def test_malformed_instance_id_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': ['not-an-id'],
            'command': 'describe',
        })
        assert result['failed']
        expected_msg = "Malformed instance IDs: ['not-an-id']"
        assert result['result']['msg'] == expected_msg, "Expected {expected_msg} but got {result_msg}".format(expected_msg=expected_msg, result_msg=result['result']['msg'])

    def test_valid_instance_id_pattern(self):
        assert ec2_instance_state.INSTANCE_ID_RE.match('i-0123456789abcdef0')
        assert ec2_instance_state.INSTANCE_ID_RE.match('i-12345678')
        assert not ec2_instance_state.INSTANCE_ID_RE.match('i-XYZ')
        assert not ec2_instance_state.INSTANCE_ID_RE.match('foo')
        assert not ec2_instance_state.INSTANCE_ID_RE.match('i-123456789')  # 9-char is invalid


class FakeEC2Client:
    """
    Minimal stand-in for boto3.client('ec2') used in tests.

    - instances_by_id: dict mapping instance id -> dict of fields used by the module.
                       Required field: 'state' (one of running/stopped/pending/stopping/terminated/...).
                       Optional fields: instance_type, availability_zone, private_ip,
                       public_ip, tags, launch_time. Sensible defaults supplied.
    - missing_ids:    set of IDs that should raise InvalidInstanceID.NotFound when described.
    - calls:          ordered list of (method_name, kwargs) recorded for assertions.
    """

    def __init__(self, instances_by_id=None, missing_ids=None):
        self.instances_by_id = dict(instances_by_id or {})
        self.missing_ids = set(missing_ids or [])
        self.calls = []
        self.waiters_invoked = []  # list of (waiter_name, instance_ids)

    def describe_instances(self, InstanceIds):
        self.calls.append(('describe_instances', {'InstanceIds': list(InstanceIds)}))
        bad = [i for i in InstanceIds if i in self.missing_ids]
        if bad:
            from botocore.exceptions import ClientError
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'InvalidInstanceID.NotFound',
                        'Message': f'Instances not found: {bad}',
                    }
                },
                operation_name='DescribeInstances',
            )
        reservations = []
        for iid in InstanceIds:
            data = self.instances_by_id.get(iid, {})
            inst = {
                'InstanceId': iid,
                'State': {'Name': data.get('state', 'running')},
                'InstanceType': data.get('instance_type', 't3.micro'),
                'Placement': {'AvailabilityZone': data.get('availability_zone', 'us-east-1a')},
                'PrivateIpAddress': data.get('private_ip', '10.0.0.1'),
                'PublicIpAddress': data.get('public_ip'),
                'Tags': [{'Key': k, 'Value': v} for k, v in data.get('tags', {}).items()],
                'LaunchTime': data.get('launch_time', '2026-04-13T12:00:00+00:00'),
            }
            reservations.append({'Instances': [inst]})
        return {'Reservations': reservations}

    
    def start_instances(self, InstanceIds):
        self.calls.append(('start_instances', {'InstanceIds': list(InstanceIds)}))
        starts = []
        for iid in InstanceIds:
            prev = self.instances_by_id.get(iid, {}).get('state', 'stopped')
            self.instances_by_id.setdefault(iid, {})['state'] = 'pending'
            starts.append({
                'InstanceId': iid,
                'CurrentState': {'Name': 'pending'},
                'PreviousState': {'Name': prev},
            })
        return {'StartingInstances': starts}

    def stop_instances(self, InstanceIds):
        self.calls.append(('stop_instances', {'InstanceIds': list(InstanceIds)}))
        stops = []
        for iid in InstanceIds:
            prev = self.instances_by_id.get(iid, {}).get('state', 'running')
            self.instances_by_id.setdefault(iid, {})['state'] = 'stopping'
            stops.append({
                'InstanceId': iid,
                'CurrentState': {'Name': 'stopping'},
                'PreviousState': {'Name': prev},
            })
        return {'StoppingInstances': stops}

    def get_waiter(self, name):
        client = self
        end_state = {'instance_running': 'running', 'instance_stopped': 'stopped'}[name]

        class _Waiter:
            def wait(self, InstanceIds, WaiterConfig=None):
                client.waiters_invoked.append((name, list(InstanceIds)))
                # Simulate state advance.
                for iid in InstanceIds:
                    client.instances_by_id.setdefault(iid, {})['state'] = end_state
        return _Waiter()
