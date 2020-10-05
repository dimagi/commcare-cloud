from __future__ import print_function

from __future__ import absolute_import
from __future__ import unicode_literals
import pickle
from ipaddress import ip_address
from parameterized import parameterized

from commcare_cloud.environment.main import Environment, get_environment
from commcare_cloud.environment.paths import get_available_envs


commcare_envs = [
    (env,) for env in (
        get_environment(env_name) for env_name in get_available_envs()
    )
    if not env.meta_config.bare_non_cchq_environment
]


@parameterized(commcare_envs)
def test_all(environment):
    environment.check()


@parameterized(commcare_envs)
def test_hostnames(environment):
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


@parameterized(commcare_envs)
def test_pickle_environment(environment):
    properties = [property_name for property_name in dir(Environment) if
                  isinstance(getattr(Environment, property_name), property)]
    # Call each property so it will get pickled
    for prop in properties:
        getattr(environment, prop)

    pickled_env = pickle.dumps(environment)
    loaded_env = pickle.loads(pickled_env)
    pickle.dumps(loaded_env)
