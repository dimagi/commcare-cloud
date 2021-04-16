from functools import cached_property


class RemoteConf:
    """Reference config on the remote system.

    The paths here are redundant with ansible/group_vars/all.yml"""
    def __init__(self, environment):
        self.environment = environment
        # the default 'cchq' is redundant with ansible/group_vars/all.yml
        self.cchq_user = environment.public_vars.get('cchq_user', 'cchq')
        self.deploy_env = environment.meta_config.deploy_env

    @cached_property
    def code_current(self):
        return '/home/{cchq_user}/www/{deploy_env}/current'.format(
            cchq_user=self.cchq_user, deploy_env=self.deploy_env)

    def release(self, release_name):
        return '/home/{cchq_user}/www/{deploy_env}/releases/{release}'.format(
            cchq_user=self.cchq_user, deploy_env=self.deploy_env, release=release_name)
