from memoized import memoized_property


class RemoteConf:
    """Reference config on the remote system.

    The paths here are redundant with ansible/group_vars/all.yml"""
    def __init__(self, environment):
        self.environment = environment
        # the default 'cchq' is redundant with ansible/group_vars/all.yml
        self.cchq_user = environment.public_vars.get('cchq_user', 'cchq')
        self.deploy_env = environment.meta_config.deploy_env

    @memoized_property
    def code_current(self):
        return f'/home/{self.cchq_user}/www/{self.deploy_env}/current'

    def release(self, release_name):
        return f'/home/{self.cchq_user}/www/{self.deploy_env}/releases/{release_name}'
