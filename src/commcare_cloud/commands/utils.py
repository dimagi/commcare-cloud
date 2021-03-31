from __future__ import absolute_import
from __future__ import unicode_literals

import os
from string import Formatter

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


def strfdelta(tdelta, fmt='{D:02}d {H:02}h {M:02}m {S:02}s'):
    """Convert a datetime.timedelta object or a regular number to a custom-
    formatted string, just like the stftime() method does for datetime.datetime
    objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
        '{H}h {S}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'

    From https://stackoverflow.com/a/42320260/632517
    """
    remainder = int(tdelta.total_seconds())

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('W', 'D', 'H', 'M', 'S')
    constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            values[field], remainder = divmod(remainder, constants[field])
    return f.format(fmt, **values)
