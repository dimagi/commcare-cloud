import os
from ..environment import FABFILE
from six.moves import shlex_quote


class Fab(object):
    command = 'fab'
    help = (
        "Run a fab command as you would with fab"
    )

    @staticmethod
    def make_parser(parser):
        parser.add_argument(dest='fab_command', help="fab command", default=None)

    @staticmethod
    def run(args, unknown_args):
        cmd_parts = (
            'fab', '-f', FABFILE,
            args.environment,
        ) + (
            (args.fab_command,) if args.fab_command else ()
        ) + tuple(unknown_args)
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print(cmd)
        os.execvp('fab', cmd_parts)
