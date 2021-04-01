from __future__ import absolute_import
from __future__ import unicode_literals

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

    def run_command(self, hosts, parallel_pool_size=1):
        from fabric.api import execute, sudo, env, parallel
        if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
            env.use_ssh_config = True
        env.forward_agent = True
        # pass `-E` to sudo to preserve environment for ssh agent forwarding
        env.sudo_prefix = "sudo -SE -p '%(sudo_prompt)s' "
        env.user = self.user_name
        env.password = self.password
        env.hosts = hosts
        env.warn_only = True

        def _task():
            result = sudo(self.command, user=self.user_as)
            return result

        task = _task
        if parallel_pool_size > 1:
            task = parallel(pool_size=parallel_pool_size)(_task)

        res = execute(task)
        return res


def timeago(tdelta):
    # https://github.com/hustcc/timeago (the good bits)
    # second, minute, hour, day, week, month, year(365 days)
    BUCKETS = [60.0, 60.0, 24.0, 7.0, 365.0 / 7.0 / 12.0, 12.0]
    TEMPLATES = [
        "just now",
        "%s seconds ago",
        "1 minute ago",
        "%s minutes ago",
        "1 hour ago",
        "%s hours ago",
        "1 day ago",
        "%s days ago",
        "1 week ago",
        "%s weeks ago",
        "1 month ago",
        "%s months ago",
        "1 year ago",
        "%s years ago",
    ]
    diff_seconds = int(tdelta.total_seconds())
    i = 0
    while i < len(BUCKETS):
        tmp = BUCKETS[i]
        if diff_seconds >= tmp:
            i += 1
            diff_seconds /= tmp
        else:
            break
    diff_seconds = int(diff_seconds)
    i *= 2

    # 'just now' is within 10s
    if diff_seconds > (9 if i == 0 else 1):
        i += 1

    template = TEMPLATES[i]
    return '%s' in template and template % diff_seconds or template
