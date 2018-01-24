import os
from .command_base import CommandBase
from ..environment import FABFILE
from six.moves import shlex_quote


class Fab(CommandBase):
    command = 'fab'
    help = (
        "Run a fab command as you would with fab"
    )

    def make_parser(self):
        self.parser.add_argument(dest='fab_command', help="fab command", default=None)

    def run(self, args, unknown_args):
        cmd_parts = (
            'fab', '-f', FABFILE,
            args.environment,
        ) + (
            (args.fab_command,) if args.fab_command else ()
        ) + tuple(unknown_args)
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print(cmd)
        os.execvp('fab', cmd_parts)
