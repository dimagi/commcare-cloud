import os

from jinja2 import Environment, FileSystemLoader


def render_template(name, context, template_root):
    env = Environment(loader=FileSystemLoader(template_root))
    return env.get_template(name).render(context)


class PrivilegedCommand():
    """
    This Class allows to execute sudo commands over ssh.
    """
    def __init__(self, user_name, password, command, user_as=None):
        """
        :param user_name: Username to login with
        :param password: Password of the user
        :param command: command to execute (This command will be executed using sudo. )
        """
        self.user_name = user_name
        self.password = password
        self.command = command
        self.user_as = user_as

    def run_parallel_command(self, hosts):
        from fabric.api import execute, sudo, env
        if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
            env.use_ssh_config = True
        env.forward_agent = True
        env.user = self.user_name
        env.password = self.password
        env.hosts = hosts
        env.warn_only = True

        def _task():
            result = sudo(self.command, user=self.user_as)
            return result

        res = execute(_task)
        return res
