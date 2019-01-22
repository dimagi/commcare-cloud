from commcare_cloud.environment.main import get_environment


def host_from_alias(hostname, environment_name):
    if environment_name == 'dev':
        # hack to avoid an inventory parsing error
        environment_name = 'development'
    env = get_environment(environment_name)
    return env.translate_host(hostname, 'custom host_from_alias filter plugin')


class FilterModule(object):
    """
    A custom ansible filter to get hostname from a host alias
        that is defined in the inventory.

    Usage: {{ <host_alias> | host_from_alias(<deploy_env>)}}.

    For e.g. {{ 'db1' | host_from_alias('development')}}.
        will return the actual hostname which is 192.168.33.16
    """
    def filters(self):
        return {
            'host_from_alias': host_from_alias
        }
