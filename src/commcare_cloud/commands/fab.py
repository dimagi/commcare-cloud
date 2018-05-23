import os
import subprocess

from memoized import memoized

from commcare_cloud.cli_utils import print_command
from .command_base import CommandBase, Argument
from ..environment.paths import FABFILE
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
        """)
    )

    def modify_parser(self):

        class _Parser(self.parser.__class__):
            @property
            @memoized
            def epilog(self):
                return subprocess.check_output(['fab', '-f', FABFILE, '-l'])

        self.parser.__class__ = _Parser

    def run(self, args, unknown_args):
        fab_args = []
        if args.fab_command:
            fab_args.append(args.fab_command)
        fab_args.extend(unknown_args)
        if args.l:
            fab_args.append('-l')
        return exec_fab_command(args.env_name, *fab_args)


def exec_fab_command(env_name, *extra_args):
    cmd_parts = (
        'fab', '-f', FABFILE,
        env_name,
    ) + tuple(extra_args)
    cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
    print_command(cmd)
    os.execvp('fab', cmd_parts)
