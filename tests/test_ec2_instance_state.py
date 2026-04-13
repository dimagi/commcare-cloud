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
    warnings_collected = []

    def fake_exit(self, **kwargs):
        kwargs.setdefault('warnings', list(warnings_collected))
        captured['result'] = kwargs
        captured['failed'] = False
        raise ModuleExitException(kwargs)

    def fake_fail(self, **kwargs):
        kwargs.setdefault('warnings', list(warnings_collected))
        captured['result'] = kwargs
        captured['failed'] = True
        raise ModuleExitException(kwargs)

    def fake_warn(self, msg):
        warnings_collected.append(msg)

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
         patch.object(ec2_instance_state.AnsibleModule, 'exit_json', new=fake_exit), \
         patch.object(ec2_instance_state.AnsibleModule, 'fail_json', new=fake_fail), \
         patch.object(ec2_instance_state.AnsibleModule, 'warn', new=fake_warn):

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

    def test_started_stopping_with_no_wait_fails_fast(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopping'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'state': 'started', 'wait': False},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('stopping', result['result']['msg'].lower())
        self.assertIn('wait', result['result']['msg'].lower())
        # No StartInstances call should have been made.
        self.assertNotIn('start_instances', [c[0] for c in fake.calls])

    def test_started_noop_does_single_describe(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started'},
            fake_client=fake,
        )
        describe_calls = [c for c in fake.calls if c[0] == 'describe_instances']
        self.assertEqual(len(describe_calls), 1,
                         "no-op path should only describe once, not twice")


class TestStopped(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_stopped_already_stopped_is_noop(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertFalse(result['result']['changed'])
        self.assertEqual(result['result']['skipped_instance_ids'], ['i-0aaaaaaaaaaaaaaaa'])
        self.assertNotIn('stop_instances', [c[0] for c in fake.calls])

    def test_stopped_running_invokes_stop_and_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        stop_calls = [c for c in fake.calls if c[0] == 'stop_instances']
        self.assertEqual(len(stop_calls), 1)
        self.assertEqual(stop_calls[0][1]['InstanceIds'], ['i-0aaaaaaaaaaaaaaaa'])
        self.assertEqual(fake.waiters_invoked, [('instance_stopped', ['i-0aaaaaaaaaaaaaaaa'])])
        self.assertEqual(result['result']['instances'][0]['current_state'], 'stopped')
        self.assertEqual(result['result']['instances'][0]['previous_state'], 'running')

    def test_stopped_no_wait_skips_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped', 'wait': False},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        self.assertEqual(fake.waiters_invoked, [])
        self.assertEqual(result['result']['instances'][0]['current_state'], 'stopping')

    def test_stopped_already_stopping_waits_but_changed_false(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopping'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        # We did not initiate the stop, so changed=false.
        self.assertFalse(result['result']['changed'])
        # No stop_instances call.
        self.assertNotIn('stop_instances', [c[0] for c in fake.calls])
        # We did wait for it to reach stopped.
        self.assertEqual(fake.waiters_invoked, [('instance_stopped', ['i-0aaaaaaaaaaaaaaaa'])])

    def test_stopped_terminated_fails(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('terminated', result['result']['msg'].lower())

    def test_stopped_noop_does_single_describe(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped'},
            fake_client=fake,
        )
        describe_calls = [c for c in fake.calls if c[0] == 'describe_instances']
        self.assertEqual(len(describe_calls), 1,
                         "no-op path should only describe once, not twice")

    def test_stopped_pending_waits_for_running_first(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'pending'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'stopped'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        # First waiter: wait for running; second: wait for stopped.
        self.assertEqual(
            fake.waiters_invoked,
            [('instance_running', ['i-0aaaaaaaaaaaaaaaa']),
             ('instance_stopped', ['i-0aaaaaaaaaaaaaaaa'])],
        )
        stop_calls = [c for c in fake.calls if c[0] == 'stop_instances']
        self.assertEqual(len(stop_calls), 1)
        self.assertEqual(stop_calls[0][1]['InstanceIds'], ['i-0aaaaaaaaaaaaaaaa'])


class TestRestarted(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_restarted_running_does_stop_then_start(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'restarted'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        # Order: stop_instances came before start_instances.
        method_order = [c[0] for c in fake.calls if c[0] in ('stop_instances', 'start_instances')]
        self.assertEqual(method_order, ['stop_instances', 'start_instances'])
        # Both waiters fired in the right order.
        waiter_order = [w[0] for w in fake.waiters_invoked]
        self.assertEqual(waiter_order, ['instance_stopped', 'instance_running'])
        self.assertEqual(result['result']['instances'][0]['previous_state'], 'running')
        self.assertEqual(result['result']['instances'][0]['current_state'], 'running')
        self.assertEqual(result['result']['state'], 'restarted')
        self.assertEqual(
            result['result']['diff'],
            {'before': {'states': {'i-0aaaaaaaaaaaaaaaa': 'running'}},
             'after':  {'states': {'i-0aaaaaaaaaaaaaaaa': 'running'}}},
        )

    def test_restarted_stopped_just_starts(self):
        # Mixed-state semantics: an already-stopped instance still ends up running
        # after a 'restarted' call.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'restarted'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        method_order = [c[0] for c in fake.calls if c[0] in ('stop_instances', 'start_instances')]
        # No stop call (already stopped); start was issued.
        self.assertEqual(method_order, ['start_instances'])
        self.assertEqual(result['result']['instances'][0]['current_state'], 'running')

    def test_restarted_with_wait_false_emits_warning(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'state': 'restarted', 'wait': False},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        # Stop phase still waits despite wait=False.
        self.assertIn(('instance_stopped', ['i-0aaaaaaaaaaaaaaaa']), fake.waiters_invoked)
        # Start phase did not wait.
        self.assertNotIn(('instance_running', ['i-0aaaaaaaaaaaaaaaa']), fake.waiters_invoked)
        # A warning was emitted on the result.
        self.assertIn('warnings', result['result'])
        self.assertTrue(any('wait' in w.lower() for w in result['result']['warnings']))

    def test_restarted_terminated_fails(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'restarted'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('terminated', result['result']['msg'].lower())


class TestCheckMode(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_started_check_mode_no_api_mutation(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'state': 'started', '_ansible_check_mode': True},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        self.assertNotIn('start_instances', [c[0] for c in fake.calls])
        self.assertEqual(fake.waiters_invoked, [])

    def test_stopped_check_mode_no_api_mutation(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'state': 'stopped', '_ansible_check_mode': True},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        self.assertNotIn('stop_instances', [c[0] for c in fake.calls])
        self.assertEqual(fake.waiters_invoked, [])


class TestInvalidIdMutating(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_started_invalid_id_fails_cleanly(self):
        fake = FakeEC2Client(missing_ids={'i-0deadbeefdeadbeef'})
        result = run_module(
            {'instance_ids': ['i-0deadbeefdeadbeef'], 'state': 'started'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('NotFound', result['result']['msg'])


class TestWaiterTimeout(unittest.TestCase):

    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        os.environ.pop('AWS_REGION', None)

    def test_waiter_timeout_fails_cleanly(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })

        # Patch get_waiter to return a waiter that always raises.
        from botocore.exceptions import WaiterError
        class _BoomWaiter:
            def wait(self, InstanceIds, WaiterConfig=None):
                raise WaiterError(name='instance_running', reason='timeout', last_response={})
        fake.get_waiter = lambda name: _BoomWaiter()

        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('Waiter', result['result']['msg'])
        self.assertIn('instance_running', result['result']['msg'])


if __name__ == '__main__':
    unittest.main()
