import os
import re
import subprocess

from memoized import memoized

from commcare_cloud.cli_utils import print_command, check_branch
from commcare_cloud.environment.main import get_environment
from commcare_cloud.commands import shared_args
from .command_base import CommandBase, Argument
from ..environment.paths import FABFILE, get_available_envs
from six.moves import shlex_quote


class Fab(CommandBase):
    command = 'fab'
    help = (
        "Run a fab command as you would with fab"
    )

    arguments = (
        Argument(dest='fab_command', help="""
        The name of the fab task to run. It and all following arguments
        will be passed on without modification to `fab`, so all normal `fab`
        syntax rules apply.
        """, default=None, nargs="?"),
        Argument('-l', action='store_true', help="""
        Use `-l` instead of a command to see the full list of commands.
        """),
        shared_args.BRANCH_ARG,
    )

    def modify_parser(self):

        class _Parser(self.parser.__class__):
            @property
            @memoized
            def epilog(self):
                lines = subprocess.check_output(['fab', '-f', FABFILE, '-l']).splitlines()
                return '\n'.join(
                    line for line in lines
                    if not re.match(r'^\s+({})'.format('|'.join(get_available_envs())), line)
                )

        self.parser.__class__ = _Parser

    def run(self, args, unknown_args):
        check_branch(args)
        fab_args = []
        if args.fab_command:
            fab_args.append(args.fab_command)
        fab_args.extend(unknown_args)
        if args.l:
            fab_args.append('-l')
        else:
            env = get_environment(args.env_name)
            fab_args.extend(['--disable-known-hosts',
                             '--system-known-hosts', env.paths.known_hosts])
        # Create known_hosts file if it doesn't exist
        known_hosts_file = env.paths.known_hosts
        if not os.path.isfile(known_hosts_file):
            open(known_hosts_file, 'a').close()
        return exec_fab_command(args.env_name, *fab_args)


def exec_fab_command(env_name, *extra_args):
    cmd_parts = (
        'fab', '-f', FABFILE,
        env_name,
    ) + tuple(extra_args)
    cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
    print_command(cmd)
    return subprocess.call(cmd_parts)
