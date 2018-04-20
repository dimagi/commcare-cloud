from __future__ import absolute_import

import os
import subprocess

from argparse import ArgumentParser
from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import ANSIBLE_ROLES_PATH, ANSIBLE_DIR, \
    put_virtualenv_on_the_path


class Install(CommandBase):
    command = 'install'
    help = "Finishes the commcare-cloud install, including installing ansible-galaxy roles"

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        env = os.environ.copy()
        put_virtualenv_on_the_path()
        if not os.path.exists(ANSIBLE_ROLES_PATH):
            os.makedirs(ANSIBLE_ROLES_PATH)

        env['ANSIBLE_ROLES_PATH'] = ANSIBLE_ROLES_PATH
        cmd_parts = ['ansible-galaxy', 'install', '-r', os.path.join(ANSIBLE_DIR, 'requirements.yml')]
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True, env=env)
        p.communicate()
        return p.returncode


COMMAND_TYPES = [
    Install,
]


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    commands = {}

    for command_type in COMMAND_TYPES:
        assert issubclass(command_type, CommandBase), command_type
        cmd = command_type(subparsers.add_parser(command_type.command, help=command_type.help))
        cmd.make_parser()
        commands[cmd.command] = cmd
        for alias in cmd.aliases:
            commands[alias] = cmd

    args, unknown_args = parser.parse_known_args()

    exit_code = commands[args.command].run(args, unknown_args)
    if exit_code is not 0:
        exit(exit_code)
