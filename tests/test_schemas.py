from __future__ import print_function

from __future__ import absolute_import
import itertools
import os

from mock import patch
from nose.tools import assert_equal

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.schemas.app_processes import get_machine_alias

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'test_envs')


@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_get_machine_alias():
    env = get_environment('small_cluster')

    all_hosts = set(itertools.chain.from_iterable(list(env.groups.values())))
    assert_equal(all_hosts, {'172.19.3.0', '172.19.3.1', '172.19.3.2', '172.19.3.3'})
    aliases = set([get_machine_alias(env, host) for host in all_hosts])
    assert_equal(aliases, {'demo_server0', 'demo_server1', 'demo_server2', 'demo_server3'})