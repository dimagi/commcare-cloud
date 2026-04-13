# `ec2_instance_state` Ansible Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a custom Ansible module `ec2_instance_state` that starts, stops, restarts, and describes EC2 instances by ID — with idempotency, optional waiting, and a region/auth model that matches commcare-cloud's existing env-var-based AWS conventions.

**Architecture:** Single-file Python module under `src/commcare_cloud/ansible/library/`, following the convention used by `clean_releases.py` and `setup_virtualenv.py`. Internally decomposed into small helpers (describe → filter targets → mutate → wait) for testability. Tests use stdlib `unittest.mock` to patch `boto3.client('ec2')` — no new dependencies. `restarted` is implemented as `stop(wait=True)` + `start(wait=user_choice)`.

**Tech Stack:** Python 3, `boto3` (already pinned at 1.39.3 in `requirements.txt`), Ansible's `AnsibleModule`, stdlib `unittest.mock` for testing. Test runner is `nosetests` (the repo's CI runs `nosetests -v`; see `.tests/tests.sh:43`). Tests use plain `unittest.TestCase` so they also run under `python -m unittest` if needed.

**Spec:** `docs/superpowers/specs/2026-04-13-ec2-instance-state-ansible-module-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `src/commcare_cloud/ansible/library/ec2_instance_state.py` | Create | The Ansible module: arg parsing, AWS calls, state orchestration, return-shape construction. ~250-300 lines. |
| `tests/test_ec2_instance_state.py` | Create | Unit tests using `unittest.mock` to patch `boto3.client`. Includes a `FakeEC2Client` helper class. |

The module is intentionally a single file (matches existing pattern in `library/`). Internal functions are module-level (not a class) so they're easy to import and unit-test.

---

## Internal Module Layout

The module file will have this structure (defined progressively across tasks):

```
DOCUMENTATION = """..."""
EXAMPLES = """..."""
RETURN = """..."""

VALID_STATES = ['started', 'stopped', 'restarted', 'described']
INSTANCE_ID_RE = re.compile(r'^i-[0-9a-f]{8,17}$')
# EC2 instance states from which we cannot recover to 'running'/'stopped'.
# 'terminated' is permanent; 'shutting-down' is a one-way transition to 'terminated'
# (AWS rejects StartInstances/StopInstances on either). Compare to 'stopping' which
# is reversible (-> 'stopped' -> 'pending' -> 'running').
TERMINAL_STATES = {'terminated', 'shutting-down'}

# --- helpers ---
def _get_region(params):                          # resolve region or fail
def _get_ec2_client(region):                      # boto3 client
def _describe_instances(client, instance_ids):    # dict[id -> raw_instance]
def _format_instance(raw, prev_state, cur_state): # return-shape entry
def _check_no_terminal(instances, state):         # fail if terminated/shutting-down
def _filter_targets(instances, want_state):       # ids needing change
def _do_describe(module, client, ids):
def _do_start(module, client, ids, wait, timeout, _force_wait=False):
def _do_stop(module, client, ids, wait, timeout, _force_wait=False):
def _do_restart(module, client, ids, wait, timeout):

def main():                                       # AnsibleModule + dispatch
```

---

## Task 1: Module skeleton + argument validation

**Files:**
- Create: `src/commcare_cloud/ansible/library/ec2_instance_state.py`
- Create: `tests/test_ec2_instance_state.py`

This task lays down the skeleton: docs blocks, arg spec, validation, and a `main()` that exits on `state: described` with an empty result (so we can unit-test the validation path before any AWS code exists).

- [ ] **Step 1: Write the failing test for argument validation**

Create `tests/test_ec2_instance_state.py`:

```python
import json
import re
import sys
import unittest
from unittest.mock import patch

# Add the library directory to sys.path so we can import the module by name
import os
LIBRARY_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'src', 'commcare_cloud', 'ansible', 'library'
)
sys.path.insert(0, os.path.abspath(LIBRARY_DIR))

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

    # Ansible reads args from stdin as a JSON-wrapped 'ANSIBLE_MODULE_ARGS' blob.
    stdin_payload = json.dumps({'ANSIBLE_MODULE_ARGS': args})

    with patch.object(sys, 'argv', ['ec2_instance_state']), \
         patch('sys.stdin.read', return_value=stdin_payload), \
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


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails (module doesn't exist yet)**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: ImportError or ModuleNotFoundError for `ec2_instance_state`.

- [ ] **Step 3: Create the module skeleton**

Create `src/commcare_cloud/ansible/library/ec2_instance_state.py`:

```python
#! /usr/bin/env python3
"""Custom Ansible module to start/stop/restart/describe EC2 instances."""
import os
import re

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type


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

    _get_region(module)

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: All 5 tests in `TestArgumentValidation` pass.

- [ ] **Step 5: Commit**

```bash
git add src/commcare_cloud/ansible/library/ec2_instance_state.py tests/test_ec2_instance_state.py
git commit -m "Add ec2_instance_state module skeleton with arg validation"
```

---

## Task 2: `described` state

Implements describe + return-shape formatting. After this task, `state: described` returns real instance data.

**Files:**
- Modify: `src/commcare_cloud/ansible/library/ec2_instance_state.py`
- Modify: `tests/test_ec2_instance_state.py`

- [ ] **Step 1: Add the FakeEC2Client helper and `described` tests**

Append to `tests/test_ec2_instance_state.py` (above `if __name__ == '__main__':`):

```python
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
        ids = ['i-0aaaaaaaaaaaaaaaa', 'i-0bbbbbbbbbbbbbbbb', 'i-0ccccccccccccccccc']
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
```

- [ ] **Step 2: Run the new tests; expect failures (described isn't implemented yet)**

Run: `nosetests tests/test_ec2_instance_state.py:TestDescribed -v`
Expected: All 4 fail (current `main()` returns empty `instances: []`).

- [ ] **Step 3: Implement the describe pathway**

Edit `src/commcare_cloud/ansible/library/ec2_instance_state.py`. Replace the stub `main()` body and add helpers above it.

Add these helpers above `main()`:

```python
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
    from botocore.exceptions import ClientError
    try:
        raw_by_id = _describe_instances(client, instance_ids)
    except ClientError as e:
        module.fail_json(msg="AWS DescribeInstances failed: {}".format(e))
    # Order output to match input.
    formatted = []
    states = {}
    for iid in instance_ids:
        raw = raw_by_id.get(iid)
        if raw is None:
            module.fail_json(msg="Instance {} missing from DescribeInstances response.".format(iid))
        state = raw['State']['Name']
        states[iid] = state
        formatted.append((iid, raw, state))
    return formatted, states  # list of (id, raw, state); dict id->state
```

Replace `main()` so the bottom of the function dispatches by state. Keep the existing validation; replace only the dispatch stub.

```python
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
    else:
        # Other states implemented in subsequent tasks; placeholder fail.
        module.fail_json(msg="State {!r} not yet implemented.".format(state))


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
```

- [ ] **Step 4: Run the described tests; expect pass**

Run: `nosetests tests/test_ec2_instance_state.py:TestDescribed -v`
Expected: All 4 pass.

- [ ] **Step 5: Run the full test file to confirm no regression**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: 9 tests pass (5 validation + 4 described).

- [ ] **Step 6: Commit**

```bash
git add src/commcare_cloud/ansible/library/ec2_instance_state.py tests/test_ec2_instance_state.py
git commit -m "ec2_instance_state: implement 'described' state"
```

---

## Task 3: `started` state

**Files:**
- Modify: `src/commcare_cloud/ansible/library/ec2_instance_state.py`
- Modify: `tests/test_ec2_instance_state.py`

- [ ] **Step 1: Add `started` tests**

Append to `tests/test_ec2_instance_state.py` (above `if __name__ == '__main__':`):

```python
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
            'i-0ccccccccccccccccc': {'state': 'stopped'},  # needs start
        })
        result = run_module(
            {'instance_ids': [
                'i-0aaaaaaaaaaaaaaaa',
                'i-0bbbbbbbbbbbbbbbb',
                'i-0ccccccccccccccccc',
            ], 'state': 'started'},
            fake_client=fake,
        )
        self.assertFalse(result['failed'])
        self.assertTrue(result['result']['changed'])
        start_calls = [c for c in fake.calls if c[0] == 'start_instances']
        self.assertEqual(len(start_calls), 1)
        self.assertEqual(
            sorted(start_calls[0][1]['InstanceIds']),
            ['i-0bbbbbbbbbbbbbbbb', 'i-0ccccccccccccccccc'],
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
```

- [ ] **Step 2: Run new tests; expect failures**

Run: `nosetests tests/test_ec2_instance_state.py:TestStarted -v`
Expected: All 5 fail (started raises "not yet implemented").

- [ ] **Step 3: Implement helpers and `_do_start`**

Edit `src/commcare_cloud/ansible/library/ec2_instance_state.py`. Add these helpers (after `_describe_and_format`):

```python
def _check_no_terminal(formatted, action_state, module):
    """Fail the module if any instance is terminated/shutting-down."""
    bad = [(iid, state) for (iid, _raw, state) in formatted if state in TERMINAL_STATES]
    if bad:
        module.fail_json(msg=(
            "Cannot {} terminated/shutting-down instances: {}".format(
                action_state, ', '.join('{}={}'.format(i, s) for i, s in bad)
            )
        ))


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
```

Add `_do_start`:

```python
def _do_start(module, client, instance_ids, wait, timeout):
    formatted, before_states = _describe_and_format(client, instance_ids, module)
    _check_no_terminal(formatted, 'start', module)

    targets_needing_start = [iid for (iid, _raw, state) in formatted
                             if state in ('stopped', 'stopping')]
    skipped = [iid for iid in instance_ids if iid not in targets_needing_start]

    # If any instance is currently 'stopping' and we'll need to start it, wait for stopped first.
    stopping_now = [iid for (iid, _raw, state) in formatted if state == 'stopping']
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

        if wait:
            _wait_for(client, 'instance_running', targets_needing_start, timeout, module)

    _emit_result(module, client, instance_ids, before_states, after_states=None,
                 state='started', changed=changed, skipped=skipped, refresh=True)


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
```

Update the dispatch in `main()` to call `_do_start` for `started`:

Find:
```python
    if state == 'described':
        _do_describe(module, client, instance_ids)
    else:
        # Other states implemented in subsequent tasks; placeholder fail.
        module.fail_json(msg="State {!r} not yet implemented.".format(state))
```

Replace with:
```python
    if state == 'described':
        _do_describe(module, client, instance_ids)
    elif state == 'started':
        _do_start(module, client, instance_ids, params['wait'], params['wait_timeout'])
    else:
        module.fail_json(msg="State {!r} not yet implemented.".format(state))
```

- [ ] **Step 4: Run TestStarted; expect pass**

Run: `nosetests tests/test_ec2_instance_state.py:TestStarted -v`
Expected: All 5 pass.

- [ ] **Step 5: Full file regression check**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: 14 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/commcare_cloud/ansible/library/ec2_instance_state.py tests/test_ec2_instance_state.py
git commit -m "ec2_instance_state: implement 'started' state with idempotency and waiter"
```

---

## Task 4: `stopped` state

Mirrors `started` with opposite semantics.

**Files:**
- Modify: `src/commcare_cloud/ansible/library/ec2_instance_state.py`
- Modify: `tests/test_ec2_instance_state.py`

- [ ] **Step 1: Add `stopped` tests**

Append to `tests/test_ec2_instance_state.py`:

```python
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
```

- [ ] **Step 2: Run new tests; expect failures**

Run: `nosetests tests/test_ec2_instance_state.py:TestStopped -v`
Expected: All 5 fail.

- [ ] **Step 3: Implement `_do_stop`**

Add to `src/commcare_cloud/ansible/library/ec2_instance_state.py` (after `_do_start`):

```python
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

    # Wait for both initiated and already-in-progress stops if wait=True.
    if wait:
        wait_for = list(targets_needing_stop) + list(already_stopping)
        if wait_for:
            _wait_for(client, 'instance_stopped', wait_for, timeout, module)

    _emit_result(module, client, instance_ids, before_states, after_states=None,
                 state='stopped', changed=changed, skipped=skipped, refresh=True)
```

Update dispatch in `main()`:

Find:
```python
    elif state == 'started':
        _do_start(module, client, instance_ids, params['wait'], params['wait_timeout'])
    else:
        module.fail_json(msg="State {!r} not yet implemented.".format(state))
```

Replace with:
```python
    elif state == 'started':
        _do_start(module, client, instance_ids, params['wait'], params['wait_timeout'])
    elif state == 'stopped':
        _do_stop(module, client, instance_ids, params['wait'], params['wait_timeout'])
    else:
        module.fail_json(msg="State {!r} not yet implemented.".format(state))
```

- [ ] **Step 4: Run TestStopped; expect pass**

Run: `nosetests tests/test_ec2_instance_state.py:TestStopped -v`
Expected: All 5 pass.

- [ ] **Step 5: Full file regression check**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: 19 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/commcare_cloud/ansible/library/ec2_instance_state.py tests/test_ec2_instance_state.py
git commit -m "ec2_instance_state: implement 'stopped' state with idempotency and waiter"
```

---

## Task 5: `restarted` state

`restarted` calls `_do_stop` with `wait=True` (forced), then `_do_start` with the user's `wait` param. To avoid double `exit_json`, both inner functions need to be refactored slightly so that they return their result instead of always calling `exit_json` directly. We'll thread that through with a `_emit=True` parameter.

**Files:**
- Modify: `src/commcare_cloud/ansible/library/ec2_instance_state.py`
- Modify: `tests/test_ec2_instance_state.py`

- [ ] **Step 1: Add `restarted` tests**

Append to `tests/test_ec2_instance_state.py`:

```python
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
```

Note: the `warnings` field on `exit_json` output is provided by Ansible's `AnsibleModule` automatically when `module.warn()` is called. The `run_module` helper captures the kwargs passed to `exit_json`, so `warnings` shows up only if the real `AnsibleModule` includes it. Since we patch `exit_json` we will pass warnings through manually. Update the test helper to also capture `module.warn()` calls.

Replace `run_module` in the test file with this version (full replacement of the function):

```python
def run_module(args, fake_client=None):
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

    stdin_payload = json.dumps({'ANSIBLE_MODULE_ARGS': args})

    with patch.object(sys, 'argv', ['ec2_instance_state']), \
         patch('sys.stdin.read', return_value=stdin_payload), \
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
```

- [ ] **Step 2: Run TestRestarted; expect failures**

Run: `nosetests tests/test_ec2_instance_state.py:TestRestarted -v`
Expected: All 4 fail (restarted not implemented).

- [ ] **Step 3: Refactor `_do_start` and `_do_stop` to optionally return without emitting**

Edit `src/commcare_cloud/ansible/library/ec2_instance_state.py`. Change `_do_start` and `_do_stop` to accept an `emit` parameter (default `True`). When `emit=False`, instead of calling `_emit_result`, return a dict with the data needed to combine with the next phase.

Update `_do_start` signature and the two `_emit_result` callsites:

```python
def _do_start(module, client, instance_ids, wait, timeout, emit=True):
    formatted, before_states = _describe_and_format(client, instance_ids, module)
    _check_no_terminal(formatted, 'start', module)

    targets_needing_start = [iid for (iid, _raw, state) in formatted
                             if state in ('stopped', 'stopping')]
    skipped = [iid for iid in instance_ids if iid not in targets_needing_start]

    stopping_now = [iid for (iid, _raw, state) in formatted if state == 'stopping']
    if wait and stopping_now:
        _wait_for(client, 'instance_stopped', stopping_now, timeout, module)

    changed = bool(targets_needing_start)

    if module.check_mode:
        after_states = dict(before_states)
        for iid in targets_needing_start:
            after_states[iid] = 'running' if wait else 'pending'
        return _result_or_emit(module, client, instance_ids, before_states, after_states,
                               state='started', changed=changed, skipped=skipped,
                               refresh=False, emit=emit)

    if targets_needing_start:
        try:
            client.start_instances(InstanceIds=targets_needing_start)
        except Exception as e:  # noqa: BLE001
            module.fail_json(msg="StartInstances failed: {}".format(e))

        if wait:
            _wait_for(client, 'instance_running', targets_needing_start, timeout, module)

    return _result_or_emit(module, client, instance_ids, before_states, after_states=None,
                           state='started', changed=changed, skipped=skipped,
                           refresh=True, emit=emit)
```

Same change for `_do_stop`:

```python
def _do_stop(module, client, instance_ids, wait, timeout, emit=True):
    formatted, before_states = _describe_and_format(client, instance_ids, module)
    _check_no_terminal(formatted, 'stop', module)

    targets_needing_stop = [iid for (iid, _raw, state) in formatted
                            if state in ('running', 'pending')]
    already_stopping = [iid for (iid, _raw, state) in formatted if state == 'stopping']
    skipped = [iid for iid in instance_ids
               if iid not in targets_needing_stop and iid not in already_stopping]

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
        return _result_or_emit(module, client, instance_ids, before_states, after_states,
                               state='stopped', changed=changed, skipped=skipped,
                               refresh=False, emit=emit)

    if targets_needing_stop:
        try:
            client.stop_instances(InstanceIds=targets_needing_stop)
        except Exception as e:  # noqa: BLE001
            module.fail_json(msg="StopInstances failed: {}".format(e))

    if wait:
        wait_for = list(targets_needing_stop) + list(already_stopping)
        if wait_for:
            _wait_for(client, 'instance_stopped', wait_for, timeout, module)

    return _result_or_emit(module, client, instance_ids, before_states, after_states=None,
                           state='stopped', changed=changed, skipped=skipped,
                           refresh=True, emit=emit)
```

Replace `_emit_result` with `_result_or_emit`:

```python
def _result_or_emit(module, client, instance_ids, before_states, after_states,
                    state, changed, skipped, refresh, emit):
    """Build the result payload. If emit is True, call exit_json; else return the dict."""
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
    payload = {
        'changed': changed,
        'state': state,
        'instances': instances,
        'skipped_instance_ids': skipped,
        'diff': {'before': {'states': before_states},
                 'after': {'states': after_states}},
    }
    if emit:
        module.exit_json(**payload)
    return payload
```

- [ ] **Step 4: Implement `_do_restart`**

Add (after `_do_stop`):

```python
def _do_restart(module, client, instance_ids, wait, timeout):
    if not wait:
        module.warn(
            "wait=False ignored for the stop phase of 'restarted'; "
            "stop must complete before start can be issued."
        )

    # Phase 1: stop, always wait.
    stop_payload = _do_stop(module, client, instance_ids, wait=True,
                            timeout=timeout, emit=False)

    # Phase 2: start, with the user's wait choice.
    start_payload = _do_start(module, client, instance_ids, wait=wait,
                              timeout=timeout, emit=False)

    # Build a combined payload:
    #   previous_state = state before stop
    #   current_state  = state after start
    before_states = stop_payload['diff']['before']['states']
    after_states = start_payload['diff']['after']['states']

    # Re-fetch instance metadata for the combined output.
    formatted, _ = _describe_and_format(client, instance_ids, module)
    raw_by_id = {iid: raw for (iid, raw, _state) in formatted}

    instances = [
        _format_instance(raw_by_id[iid], before_states[iid], after_states[iid])
        for iid in instance_ids
    ]

    # 'changed' is True if either phase mutated state.
    changed = bool(stop_payload['changed'] or start_payload['changed'])

    # 'skipped' = ids that were no-ops in BOTH phases.
    stopped_skipped = set(stop_payload['skipped_instance_ids'])
    started_skipped = set(start_payload['skipped_instance_ids'])
    skipped = sorted(stopped_skipped & started_skipped)

    module.exit_json(
        changed=changed,
        state='restarted',
        instances=instances,
        skipped_instance_ids=skipped,
        diff={'before': {'states': before_states},
              'after': {'states': after_states}},
    )
```

Update dispatch in `main()`:

Find:
```python
    elif state == 'stopped':
        _do_stop(module, client, instance_ids, params['wait'], params['wait_timeout'])
    else:
        module.fail_json(msg="State {!r} not yet implemented.".format(state))
```

Replace with:
```python
    elif state == 'stopped':
        _do_stop(module, client, instance_ids, params['wait'], params['wait_timeout'])
    elif state == 'restarted':
        _do_restart(module, client, instance_ids, params['wait'], params['wait_timeout'])
    else:
        module.fail_json(msg="Unknown state {!r}.".format(state))
```

- [ ] **Step 5: Run TestRestarted; expect pass**

Run: `nosetests tests/test_ec2_instance_state.py:TestRestarted -v`
Expected: All 4 pass.

- [ ] **Step 6: Full file regression check**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: 23 tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/commcare_cloud/ansible/library/ec2_instance_state.py tests/test_ec2_instance_state.py
git commit -m "ec2_instance_state: implement 'restarted' as stop-then-start"
```

---

## Task 6: Check mode + invalid-id error path + waiter timeout

Final correctness work. Three additions:
1. Tests confirming check mode does not call mutating APIs.
2. Test confirming an invalid instance ID surfaces a clean failure for mutating states (mirroring the `described` invalid-id test).
3. Test confirming a waiter timeout fails the module cleanly.

**Files:**
- Modify: `tests/test_ec2_instance_state.py`
- (Module changes only if tests reveal gaps; the existing implementation should already handle these.)

- [ ] **Step 1: Add `TestCheckMode`, `TestInvalidIdMutating`, and `TestWaiterTimeout`**

Append to `tests/test_ec2_instance_state.py`:

```python
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
            def wait(self, **kwargs):
                raise WaiterError(name='instance_running', reason='timeout', last_response={})
        fake.get_waiter = lambda name: _BoomWaiter()

        result = run_module(
            {'instance_ids': ['i-0aaaaaaaaaaaaaaaa'], 'state': 'started'},
            fake_client=fake,
        )
        self.assertTrue(result['failed'])
        self.assertIn('Waiter', result['result']['msg'])
```

Note on `_ansible_check_mode`: passing this key inside `ANSIBLE_MODULE_ARGS` is the documented way to trigger check mode in unit tests of `AnsibleModule`-based modules.

- [ ] **Step 2: Run all new tests**

Run: `nosetests tests/test_ec2_instance_state.py:TestCheckMode tests/test_ec2_instance_state.py:TestInvalidIdMutating tests/test_ec2_instance_state.py:TestWaiterTimeout -v`
Expected: All 4 pass without any module changes (existing implementation handles these). If any fail, fix the module — most likely cause: `_describe_and_format` not surfacing the AWS error string clearly, or check_mode bypass missing in one of the dispatch paths.

- [ ] **Step 3: Full regression**

Run: `nosetests tests/test_ec2_instance_state.py -v`
Expected: 27 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ec2_instance_state.py
git commit -m "ec2_instance_state: tests for check mode, invalid IDs, waiter timeout"
```

---

## Task 7: Manual smoke-test sanity check (no code changes)

Verify the module loads cleanly under Ansible's module loader and the docs/examples parse.

**Files:**
- (None — sanity check only)

- [ ] **Step 1: Verify module imports cleanly**

Run: `python -c "import sys; sys.path.insert(0, 'src/commcare_cloud/ansible/library'); import ec2_instance_state; print(ec2_instance_state.VALID_STATES)"`
Expected: `['started', 'stopped', 'restarted', 'described']`

- [ ] **Step 2: Verify the DOCUMENTATION/EXAMPLES/RETURN blocks parse as YAML**

Run:
```bash
python -c "
import sys, yaml
sys.path.insert(0, 'src/commcare_cloud/ansible/library')
import ec2_instance_state as m
yaml.safe_load(m.DOCUMENTATION)
yaml.safe_load(m.RETURN)
list(yaml.safe_load_all(m.EXAMPLES))  # multi-document tolerant
print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Confirm `ansible-doc` can render the module (if ansible-doc is on PATH)**

Run: `ANSIBLE_LIBRARY=src/commcare_cloud/ansible/library ansible-doc ec2_instance_state | head -30`
Expected: rendered module help; should mention `start, stop, restart`. If `ansible-doc` is not available, skip this step.

- [ ] **Step 4: No commit needed — purely a verification task.**

---

## Self-Review Notes

Spec coverage check:
- All 4 states (`started`, `stopped`, `restarted`, `described`): Tasks 2-5.
- Idempotency (no API call when already in target state): Task 3 step 1 (`test_started_already_running_is_noop`), Task 4 step 1 (`test_stopped_already_stopped_is_noop`).
- `wait` / `wait_timeout`: Tasks 3, 4 (no-wait paths); Task 6 (timeout failure).
- `region` falls back to `AWS_REGION`: Task 1 (`test_missing_region_fails`); other tests rely on the env var being set in `setUp`.
- Auth via boto3 default chain: implicit (no profile param defined).
- Mixed-state batches: Task 3 (`test_started_mixed_batch_only_targets_what_needs_change`); Task 5 (`test_restarted_stopped_just_starts`).
- `restarted` forces `wait=True` for stop phase, warns on user override: Task 5 (`test_restarted_with_wait_false_emits_warning`).
- `terminated`/`shutting-down` fails for mutating, reports for `described`: Tasks 2, 3, 4, 5.
- Invalid instance ID fails: Tasks 2 (described), 6 (mutating).
- Check mode supported: Task 6.
- Return shape (instances, skipped_instance_ids, diff): asserted across tests.
- Module skeleton + DOCUMENTATION/EXAMPLES/RETURN: Task 1.

Type/method consistency check: helper names used consistently across tasks (`_do_start`, `_do_stop`, `_do_restart`, `_do_describe`, `_describe_and_format`, `_emit_result` → renamed to `_result_or_emit` in Task 5; `_check_no_terminal`, `_wait_for`, `_format_instance`, `_get_region`, `_get_ec2_client`). The Task 5 rename is intentional and explicit.
