from __future__ import print_function

import pickle
from ipaddress import ip_address
from parameterized import parameterized

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs


@parameterized(get_available_envs())
def test_all(env):
    environment = get_environment(env)
    environment.check()


@parameterized(get_available_envs())
def test_hostnames(env):
    environment = get_environment(env)
    missing_hostnames = set()
    for group, hosts in environment.sshable_hostnames_by_group.items():
        for host in hosts:
            try:
                ip_address(host)
            except ValueError:
                pass
            else:
                hostname = environment.get_hostname(host)
                if hostname == host:
                    missing_hostnames.add(host)
    assert len(missing_hostnames) == 0, "Environment hosts missing hostnames {}".format(list(missing_hostnames))

@parameterized(get_available_envs())
def test_pickle_environment(env):
    environment = get_environment(env)
    print("environemnent: ", environment)
    pickled_env = pickle.dumps(environment)
    pickle.loads(pickled_env)
