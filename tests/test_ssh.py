import os
import subprocess

import mock
from parameterized import parameterized

from commcare_cloud.argparse14 import ArgumentParser
from commcare_cloud.commands.inventory_lookup.inventory_lookup import Ssh

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'test_ssh_envs')


@mock.patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
@mock.patch.object(subprocess, 'call')
@mock.patch('commcare_cloud.commands.inventory_lookup.inventory_lookup.print_command', lambda args: None)
def _test_ssh_args(args, ssh_args, expected_cmd_parts, mock_call):
    os.environ['COMMCARE_CLOUD_DEFAULT_USERNAME'] = ''
    Ssh(ArgumentParser()).run(args, ssh_args)
    mock_call.assert_called_with(expected_cmd_parts)


class Args(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@parameterized([
    (Args(server='demo_server0', env_name='simple_ssh'), [],
     ['ssh', '172.19.3.0', '-o', 'UserKnownHostsFile={}/simple_ssh/known_hosts'.format(TEST_ENVIRONMENTS_DIR)]),
    (Args(server='demo_server0', env_name='ssh_no_known_hosts'), [],
     ['ssh', '172.19.3.0', '-o', 'UserKnownHostsFile={}/ssh_no_known_hosts/known_hosts'.format(TEST_ENVIRONMENTS_DIR)]),
    (Args(server='demo_server0', env_name='no_strict_known_hosts'), [],
     ['ssh', '172.19.3.0', '-o', 'UserKnownHostsFile={}/no_strict_known_hosts/known_hosts'.format(TEST_ENVIRONMENTS_DIR)]),
])
def test_ssh_args(args, ssh_args, expected_cmd_parts):
    _test_ssh_args(args, ssh_args, expected_cmd_parts)
