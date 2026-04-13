import json
import re
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


if __name__ == '__main__':
    unittest.main()
