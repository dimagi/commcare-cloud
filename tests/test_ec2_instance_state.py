import os
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from . import ansible


ec2_instance_state = ansible.import_module("ec2_instance_state")


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
        expected_msg = (
            "AWS region not provided. Pass 'region' to the module, "
            "or set the AWS_REGION environment variable."
        )
        assert result['result']['msg'] == expected_msg, \
            f"Expected {expected_msg} but got {result['result']['msg']}"

    def test_invalid_command_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': ['i-0123456789abcdef0'],
            'command': 'bogus',
        })
        assert result['failed']
        expected_msg = "value of command must be one of: describe, start, stop, stop_and_start, got: bogus"
        assert result['result']['msg'] == expected_msg, \
            f"Expected {expected_msg} but got {result['result']['msg']}"

    def test_empty_instance_ids_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': [],
            'command': 'describe',
        })
        expected_msg = "'instance_ids' must be a non-empty list."
        assert result['failed']
        assert result['result']['msg'] == expected_msg, \
            f"Expected {expected_msg} but got {result['result']['msg']}"

    def test_malformed_instance_id_fails(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        result = run_module({
            'instance_ids': ['not-an-id'],
            'command': 'describe',
        })
        assert result['failed']
        expected_msg = "Malformed instance IDs: ['not-an-id']"
        assert result['result']['msg'] == expected_msg, \
            f"Expected {expected_msg} but got {result['result']['msg']}"

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


class TestDescribe(unittest.TestCase):

    def setUp(self):
        self._orig_region = os.environ.get('AWS_REGION')
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        if self._orig_region is None:
            os.environ.pop('AWS_REGION', None)
        else:
            os.environ['AWS_REGION'] = self._orig_region

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
            {'instance_ids': ['i-0123456789abcdef0'], 'command': 'describe'},
            fake_client=fake,
        )
        assert not result['failed']
        r = result['result']
        assert not r['changed']
        assert r['command'] == 'describe', r['command']
        assert len(r['instances']) == 1, len(r['instances'])
        assert r['instances'][0] == {
            'instance_id': 'i-0123456789abcdef0',
            'previous_state': 'running',
            'current_state': 'running',
            'name': 'proxy6-staging',
            'instance_type': 't3.medium',
            'availability_zone': 'us-east-1b',
            'private_ip': '10.201.10.31',
            'public_ip': '34.1.2.3',
            'tags': {'Name': 'proxy6-staging', 'Env': 'staging'},
            'launch_time': '2026-04-13T12:00:00+00:00',
        }, r['instances'][0]

    def test_described_preserves_input_order(self):
        ids = ['i-0aaaaaaaaaaaaaaaa', 'i-0bbbbbbbbbbbbbbbb', 'i-0cccccccccccccccc']
        fake = FakeEC2Client(instances_by_id={i: {'state': 'running'} for i in ids})
        result = run_module(
            {'instance_ids': ids, 'command': 'describe'},
            fake_client=fake,
        )
        assert [i['instance_id'] for i in result['result']['instances']] == ids

    def test_described_invalid_id_fails(self):
        fake = FakeEC2Client(missing_ids={'i-0deadbeefdeadbeef'})
        result = run_module(
            {'instance_ids': ['i-0deadbeefdeadbeef'], 'command': 'describe'},
            fake_client=fake,
        )
        expected_msg = (
            "AWS DescribeInstances failed: An error occurred (InvalidInstanceID.NotFound) "
            "when calling the DescribeInstances operation: "
            "Instances not found: ['i-0deadbeefdeadbeef']"
        )
        assert result['failed']
        assert result['result']['msg'] == expected_msg, result['result']['msg']

    def test_described_reorders_out_of_order_response(self):
        ids = ['i-0aaaaaaaaaaaaaaaa', 'i-0bbbbbbbbbbbbbbbb', 'i-0cccccccccccccccc']
        fake = FakeEC2Client(instances_by_id={i: {'state': 'running'} for i in ids})
        orig = fake.describe_instances
        # Return the reservations in reversed order.
        fake.describe_instances = lambda InstanceIds: {
            'Reservations': list(reversed(orig(InstanceIds)['Reservations']))
        }
        result = run_module(
            {'instance_ids': ids, 'command': 'describe'},
            fake_client=fake,
        )
        assert [i['instance_id'] for i in result['result']['instances']] == ids


class TestStart(unittest.TestCase):

    def setUp(self):
        self._orig_region = os.environ.get('AWS_REGION')
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        if self._orig_region is None:
            os.environ.pop('AWS_REGION', None)
        else:
            os.environ['AWS_REGION'] = self._orig_region

    def test_started_already_running_is_noop(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start'},
            fake_client=fake,
        )
        assert not result['failed']
        assert not result['result']['changed']
        assert result['result']['unchanged_instance_ids'] == ['i-0aaaaaaaaaaaaaaaa']
        assert 'start_instances' not in [c[0] for c in fake.calls]

    def test_started_stopped_invokes_start_and_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start'},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        # StartInstances was called with our id.
        start_calls = [c for c in fake.calls if c[0] == 'start_instances']
        assert len(start_calls) == 1
        assert start_calls[0][1]['InstanceIds'] == ['i-0aaaaaaaaaaaaaaaa']
        # instance_running waiter was invoked.
        assert fake.waiters_invoked == [('instance_running', ['i-0aaaaaaaaaaaaaaaa'])]
        # current_state reflects post-wait state.
        assert result['result']['instances'][0]['current_state'] == 'running'
        assert result['result']['instances'][0]['previous_state'] == 'stopped'

    def test_started_no_wait_skips_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start', 'wait': False},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        assert fake.waiters_invoked == []
        # current_state reflects transitional API response.
        assert result['result']['instances'][0]['current_state'] == 'pending'

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
            ], 'command': 'start'},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        start_calls = [c for c in fake.calls if c[0] == 'start_instances']
        assert len(start_calls) == 1
        assert sorted(start_calls[0][1]['InstanceIds']) == [
            'i-0bbbbbbbbbbbbbbbb', 'i-0cccccccccccccccc',
        ]
        assert result['result']['unchanged_instance_ids'] == ['i-0aaaaaaaaaaaaaaaa']

    def test_started_terminated_fails(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start'},
            fake_client=fake,
        )
        assert result['failed']
        expected_msg = "Cannot start terminated/shutting-down instances: 10.0.0.1 (i-0aaaaaaaaaaaaaaaa)=terminated"
        assert result['result']['msg'] == expected_msg, result['result']['msg']

    def test_error_message_includes_name_tag(self):
        # Errors that reference described instances surface the Name tag
        # alongside the id for readability.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated', 'tags': {'Name': 'webworker0'}},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start'},
            fake_client=fake,
        )
        assert result['failed']
        assert 'webworker0' in result['result']['msg']
        assert 'i-0aaaaaaaaaaaaaaaa' in result['result']['msg']

    def test_started_stopping_with_no_wait_waits_for_stopped_then_starts(self):
        # A 'stopping' instance is awaited to 'stopped'
        # (precondition), then started; wait=False only skips the final
        # 'running' wait.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopping'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'command': 'start', 'wait': False},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        # Precondition waiter fired for 'stopped'; final 'running' waiter did NOT.
        assert ('instance_stopped', ['i-0aaaaaaaaaaaaaaaa']) in fake.waiters_invoked
        assert ('instance_running', ['i-0aaaaaaaaaaaaaaaa']) not in fake.waiters_invoked
        assert 'start_instances' in [c[0] for c in fake.calls]
        assert result['result']['instances'][0]['current_state'] == 'pending'

    def test_started_noop_does_single_describe(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start'},
            fake_client=fake,
        )
        describe_calls = [c for c in fake.calls if c[0] == 'describe_instances']
        assert len(describe_calls) == 1, \
            "no-op path should only describe once, not twice"

    def test_started_check_mode_does_not_wait_or_start(self):
        # In check mode the module predicts the end state but must never call
        # StartInstances nor invoke any waiter.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'start',
             '_ansible_check_mode': True},
            fake_client=fake,
        )
        assert not result['failed']
        # Predicted as changed, with the projected running state.
        assert result['result']['changed']
        assert result['result']['instances'][0]['current_state'] == 'running'
        # No StartInstances call and no waiter fired.
        assert 'start_instances' not in [c[0] for c in fake.calls]
        assert fake.waiters_invoked == []


class TestStopped(unittest.TestCase):

    def setUp(self):
        self._orig_region = os.environ.get('AWS_REGION')
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        if self._orig_region is None:
            os.environ.pop('AWS_REGION', None)
        else:
            os.environ['AWS_REGION'] = self._orig_region

    def test_stopped_already_stopped_is_noop(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop'},
            fake_client=fake,
        )
        assert not result['failed']
        assert not result['result']['changed']
        assert result['result']['command'] == 'stop', result['result']['command']
        assert result['result']['unchanged_instance_ids'] == ['i-0aaaaaaaaaaaaaaaa']
        assert 'stop_instances' not in [c[0] for c in fake.calls]

    def test_stopped_running_invokes_stop_and_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop'},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        stop_calls = [c for c in fake.calls if c[0] == 'stop_instances']
        assert len(stop_calls) == 1
        assert stop_calls[0][1]['InstanceIds'] == ['i-0aaaaaaaaaaaaaaaa']
        assert fake.waiters_invoked == [('instance_stopped', ['i-0aaaaaaaaaaaaaaaa'])]
        assert result['result']['command'] == 'stop', result['result']['command']
        assert result['result']['instances'][0]['current_state'] == 'stopped'
        assert result['result']['instances'][0]['previous_state'] == 'running'

    def test_stopped_no_wait_skips_waiter(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop', 'wait': False},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        assert fake.waiters_invoked == []
        assert result['result']['instances'][0]['current_state'] == 'stopping'

    def test_stopped_already_stopping_waits_but_changed_false(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopping'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop'},
            fake_client=fake,
        )
        assert not result['failed']
        # We did not initiate the stop, so changed=false.
        assert not result['result']['changed']
        # No stop_instances call.
        assert 'stop_instances' not in [c[0] for c in fake.calls]
        # We did wait for it to reach stopped.
        assert fake.waiters_invoked == [('instance_stopped', ['i-0aaaaaaaaaaaaaaaa'])]

    def test_stopped_terminated_fails(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop'},
            fake_client=fake,
        )
        assert result['failed']
        expected_msg = (
            "Cannot stop terminated/shutting-down instances: "
            "10.0.0.1 (i-0aaaaaaaaaaaaaaaa)=terminated"
        )
        assert result['result']['msg'] == expected_msg, result['result']['msg']

    def test_stopped_noop_does_single_describe(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop'},
            fake_client=fake,
        )
        describe_calls = [c for c in fake.calls if c[0] == 'describe_instances']
        assert len(describe_calls) == 1, \
            "no-op path should only describe once, not twice"

    def test_stopped_pending_waits_for_running_first(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'pending'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop'},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        # First waiter: wait for running; second: wait for stopped.
        assert fake.waiters_invoked == [
            ('instance_running', ['i-0aaaaaaaaaaaaaaaa']),
            ('instance_stopped', ['i-0aaaaaaaaaaaaaaaa']),
        ]
        stop_calls = [c for c in fake.calls if c[0] == 'stop_instances']
        assert len(stop_calls) == 1
        assert stop_calls[0][1]['InstanceIds'] == ['i-0aaaaaaaaaaaaaaaa']

    def test_stopped_pending_with_no_wait_waits_for_running_then_stops(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'pending'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'command': 'stop', 'wait': False},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        assert ('instance_running', ['i-0aaaaaaaaaaaaaaaa']) in fake.waiters_invoked
        assert ('instance_stopped', ['i-0aaaaaaaaaaaaaaaa']) not in fake.waiters_invoked
        assert 'stop_instances' in [c[0] for c in fake.calls]
        assert result['result']['instances'][0]['current_state'] == 'stopping'

    def test_stopped_check_mode_does_not_wait_or_stop(self):
        # In check mode the module predicts the end state but must never call
        # StopInstances nor invoke any waiter.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop',
             '_ansible_check_mode': True},
            fake_client=fake,
        )
        assert not result['failed']
        # Predicted as changed, with the projected stopped state.
        assert result['result']['changed']
        assert result['result']['instances'][0]['current_state'] == 'stopped'
        # No StopInstances call and no waiter fired.
        assert 'stop_instances' not in [c[0] for c in fake.calls]
        assert fake.waiters_invoked == []


class TestStopAndStart(unittest.TestCase):

    def setUp(self):
        self._orig_region = os.environ.get('AWS_REGION')
        os.environ['AWS_REGION'] = 'us-east-1'

    def tearDown(self):
        if self._orig_region is None:
            os.environ.pop('AWS_REGION', None)
        else:
            os.environ['AWS_REGION'] = self._orig_region

    def test_stop_and_start_running_does_stop_then_start(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop_and_start'},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        # Order: stop_instances came before start_instances.
        method_order = [c[0] for c in fake.calls if c[0] in ('stop_instances', 'start_instances')]
        assert method_order == ['stop_instances', 'start_instances']
        # Both waiters fired in the right order.
        waiter_order = [w[0] for w in fake.waiters_invoked]
        assert waiter_order == ['instance_stopped', 'instance_running']
        assert result['result']['instances'][0]['previous_state'] == 'running'
        assert result['result']['instances'][0]['current_state'] == 'running'
        assert result['result']['command'] == 'stop_and_start'
        assert result['result']['diff'] == {
            'before': {'states': {'i-0aaaaaaaaaaaaaaaa': 'running'}},
            'after': {'states': {'i-0aaaaaaaaaaaaaaaa': 'running'}},
        }

    def test_stop_and_start_stopped_just_starts(self):
        # Mixed-state semantics: an already-stopped instance still ends up running
        # after a 'stop_and_start' call.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'stopped'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop_and_start'},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        method_order = [c[0] for c in fake.calls if c[0] in ('stop_instances', 'start_instances')]
        # No stop call (already stopped); start was issued.
        assert method_order == ['start_instances']
        assert result['result']['instances'][0]['current_state'] == 'running'

    def test_stop_and_start_with_wait_false_still_waits_for_stop(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'],
             'command': 'stop_and_start', 'wait': False},
            fake_client=fake,
        )
        assert not result['failed']
        # Stop phase still waits despite wait=False.
        assert ('instance_stopped', ['i-0aaaaaaaaaaaaaaaa']) in fake.waiters_invoked
        # Start phase did not wait.
        assert ('instance_running', ['i-0aaaaaaaaaaaaaaaa']) not in fake.waiters_invoked
        # No warning is emitted (the always-wait-for-stop behavior is documented).
        assert not result['result'].get('warnings')

    def test_stop_and_start_terminated_fails(self):
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'terminated'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop_and_start'},
            fake_client=fake,
        )
        assert result['failed']
        expected_msg = "Cannot stop terminated/shutting-down instances: 10.0.0.1 (i-0aaaaaaaaaaaaaaaa)=terminated"
        assert result['result']['msg'] == expected_msg, result['result']['msg']

    def test_stop_and_start_check_mode_does_not_wait_or_mutate(self):
        # In check mode neither phase mutates AWS: no stop/start calls and no
        # waiters fire, but the run is still reported as changed.
        fake = FakeEC2Client(instances_by_id={
            'i-0aaaaaaaaaaaaaaaa': {'state': 'running'},
        })
        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'command': 'stop_and_start',
             '_ansible_check_mode': True},
            fake_client=fake,
        )
        assert not result['failed']
        assert result['result']['changed']
        assert result['result']['command'] == 'stop_and_start'
        # No StopInstances/StartInstances calls and no waiter fired.
        method_calls = [c[0] for c in fake.calls if c[0] in ('stop_instances', 'start_instances')]
        assert method_calls == []
        assert fake.waiters_invoked == []
