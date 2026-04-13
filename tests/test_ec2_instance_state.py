import json
import sys
import unittest
from unittest.mock import patch

# Add the library directory to sys.path so we can import the module by name.
# We must also ensure that the tests/ directory does NOT appear before the
# library dir on sys.path, because tests/ansible.py would otherwise shadow
# the real `ansible` package when ec2_instance_state does
# `from ansible.module_utils.basic import AnsibleModule`.
import os
LIBRARY_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'src', 'commcare_cloud', 'ansible', 'library'
))
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
# Remove any existing entry for the tests/ directory from sys.path so that
# tests/ansible.py cannot shadow the real ansible package.
sys.path = [p for p in sys.path if os.path.abspath(p) != TESTS_DIR]
sys.path.insert(0, LIBRARY_DIR)

import ec2_instance_state  # noqa: E402


class ModuleExitException(Exception):
    """Raised by patched AnsibleModule.exit_json / fail_json so tests can capture results."""
    def __init__(self, kwargs):
        self.kwargs = kwargs


def run_module(args, fake_client=None):
    """
    Invoke ec2_instance_state.main() with the given args dict.

    Returns the dict that would have been passed to exit_json or fail_json.
    """
    captured = {}

    def fake_exit(**kwargs):
        captured['result'] = kwargs
        captured['failed'] = False
        raise ModuleExitException(kwargs)

    def fake_fail(**kwargs):
        captured['result'] = kwargs
        captured['failed'] = True
        raise ModuleExitException(kwargs)

    # Ansible (2.x+, Python 3) reads module args from the module_utils.basic._ANSIBLE_ARGS
    # global (bytes) rather than stdin.  Patch that directly, which is the same approach
    # used by tests/ansible.py in this repo.
    from ansible.module_utils import basic
    from ansible.module_utils.common.text.converters import to_bytes
    # Ensure _ansible_remote_tmp and _ansible_keep_remote_files are present to
    # avoid unrelated AnsibleModule init failures.
    full_args = dict(args)
    full_args.setdefault('_ansible_remote_tmp', '/tmp')
    full_args.setdefault('_ansible_keep_remote_files', False)
    encoded_args = to_bytes(json.dumps({'ANSIBLE_MODULE_ARGS': full_args}))

    with patch.object(sys, 'argv', ['ec2_instance_state']), \
         patch.object(basic, '_ANSIBLE_ARGS', encoded_args), \
         patch.object(ec2_instance_state.AnsibleModule, 'exit_json', side_effect=fake_exit), \
         patch.object(ec2_instance_state.AnsibleModule, 'fail_json', side_effect=fake_fail):

        if fake_client is not None:
            with patch.object(ec2_instance_state, '_get_ec2_client', return_value=fake_client):
                try:
                    ec2_instance_state.main()
                except ModuleExitException:
                    pass
        else:
            try:
                ec2_instance_state.main()
            except ModuleExitException:
                pass

    return captured


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
            'state': 'described',
        })
        self.assertTrue(result['failed'])
        self.assertIn('region', result['result']['msg'].lower())

    def test_invalid_state_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': ['i-0123456789abcdef0'],
            'state': 'bogus',
        })
        self.assertTrue(result['failed'])

    def test_empty_instance_ids_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': [],
            'state': 'described',
        })
        self.assertTrue(result['failed'])
        self.assertIn('instance_ids', result['result']['msg'].lower())

    def test_malformed_instance_id_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': ['not-an-id'],
            'state': 'described',
        })
        self.assertTrue(result['failed'])
        self.assertIn('instance', result['result']['msg'].lower())

    def test_valid_instance_id_pattern(self):
        # Sanity: 17-char hex suffix matches
        self.assertTrue(ec2_instance_state.INSTANCE_ID_RE.match('i-0123456789abcdef0'))
        self.assertTrue(ec2_instance_state.INSTANCE_ID_RE.match('i-12345678'))
        self.assertFalse(ec2_instance_state.INSTANCE_ID_RE.match('i-XYZ'))
        self.assertFalse(ec2_instance_state.INSTANCE_ID_RE.match('foo'))
        self.assertFalse(ec2_instance_state.INSTANCE_ID_RE.match('i-123456789'))  # 9-char is invalid


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

    # ---- describe ----
    def describe_instances(self, InstanceIds):
        self.calls.append(('describe_instances', {'InstanceIds': list(InstanceIds)}))
        bad = [i for i in InstanceIds if i in self.missing_ids]
        if bad:
            from botocore.exceptions import ClientError
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'InvalidInstanceID.NotFound',
                        'Message': 'Instances not found: {}'.format(bad),
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

    # ---- mutate ----
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

    # ---- waiters ----
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


class TestDescribed(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_described_returns_instance_shape(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0123456789abcdef0': {
                'state': 'running',
                'instance_type': 't3.medium',
                'availability_zone': 'us-east-1b',
                'private_ip': '10.201.10.31',
                'public_ip': '34.1.2.3',
                'tags': {'Name': 'proxy6-staging', 'Env': 'staging'},
            },
        })
        result = run_module(
            {'instance_ids': ['i-0123456789abcdef0'], 'state': 'described'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        r = result['result']
        self.assertFalse(r['changed'])
        self.assertEqual(r['state'], 'described')
        self.assertEqual(len(r['instances']), 1)
        inst = r['instances'][0]
        self.assertEqual(inst['instance_id'], 'i-0123456789abcdef0')
        self.assertEqual(inst['previous_state'], 'running')
        self.assertEqual(inst['current_state'], 'running')
        self.assertEqual(inst['instance_type'], 't3.medium')
        self.assertEqual(inst['availability_zone'], 'us-east-1b')
        self.assertEqual(inst['private_ip'], '10.201.10.31')
        self.assertEqual(inst['public_ip'], '34.1.2.3')
        self.assertEqual(inst['tags'], {'Name': 'proxy6-staging', 'Env': 'staging'})

    def test_described_preserves_input_order(self):
        ids = ['i-0aaaaaaaaaaaaaaaa', 'i-0bbbbbbbbbbbbbbbb', 'i-0cccccccccccccccc']
        fake = FakeEC2Client(instances_by_id={i: {'state': 'running'} for i in ids})
        result = run_module(
            {'instance_ids': ids, 'state': 'described'},
            fake_client=fake,
        )
        self.assertEqual(
            [i['instance_id'] for i in result['result']['instances']],
            ids,
        )

    def test_described_terminated_is_reported_not_failed(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0123456789abcdef0': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0123456789abcdef0'], 'state': 'described'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertEqual(result['result']['instances'][0]['current_state'], 'terminated')

    def test_described_invalid_id_fails(self):
        fake = FakeEC2Client(missing_ids={'i-0deadbeefdeadbeef'})
        result = run_module(
            {'instance_ids': ['i-0deadbeefdeadbeef'], 'state': 'described'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('NotFound', result['result']['msg'])


class TestStarted(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_started_already_running_is_noop(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertFalse(result['result']['changed'])
        self.assertEqual(result['result']['skipped_instance_ids'], ['i-0aaaaaaaaaaaaaaaa'])
        # No StartInstances call recorded.
        self.assertNotIn('start_instances', [c[0] for c in fake.calls])

    def test_started_stopped_invokes_start_and_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        # StartInstances was called with our id.
        start_calls = [c for c in fake.calls if c[0] == 'start_instances']
        self.assertEqual(len(start_calls), 1)
        self.assertEqual(start_calls[0][1]['InstanceIds'], ['i-0aaaaaaaaaaaaaaaa'])
        # instance_running waiter was invoked.
        self.assertEqual(fake.waiters_invoked, [('instance_running', ['i-0aaaaaaaaaaaaaaaa'])])
        # current_state reflects post-wait state.
        self.assertEqual(result['result']['instances'][0]['current_state'], 'running')
        self.assertEqual(result['result']['instances'][0]['previous_state'], 'stopped')

    def test_started_no_wait_skips_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started', 'wait': False},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        self.assertEqual(fake.waiters_invoked, [])
        # current_state reflects transitional API response.
        self.assertEqual(result['result']['instances'][0]['current_state'], 'pending')

    def test_started_mixed_batch_only_targets_what_needs_change(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},   # already running
            'i-0bbbbbbbbbbbbbbbb': {'state': 'stopped'},   # needs start
            'i-0cccccccccccccccc': {'state': 'stopped'},   # needs start
        })
        result = run_module(
            {'instance_ids': [
                'i-0aaaaaaaaaaaaaaaa',
                'i-0bbbbbbbbbbbbbbbb',
                'i-0cccccccccccccccc',
            ], 'state': 'started'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        start_calls = [c for c in fake.calls if c[0] == 'start_instances']
        self.assertEqual(len(start_calls), 1)
        self.assertEqual(
            sorted(start_calls[0][1]['InstanceIds']),
            ['i-0bbbbbbbbbbbbbbbb', 'i-0cccccccccccccccc'],
        )
        self.assertEqual(result['result']['skipped_instance_ids'], ['i-0aaaaaaaaaaaaaaaa'])

    def test_started_terminated_fails(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('terminated', result['result']['msg'].lower())


if __name__ == '__main__':
    unittest.main()
