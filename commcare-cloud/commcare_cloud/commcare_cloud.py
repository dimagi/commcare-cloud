# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import
import os

import sys
import warnings

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.validate_environment_settings import ValidateEnvironmentSettings
from .argparse14 import ArgumentParser

from .commands.ansible.ansible_playbook import (
    AnsiblePlaybook,
    UpdateConfig, AfterReboot, RestartElasticsearch, BootstrapUsers, DeployStack, UpdateUsers,
    Service,
)
from .commands.ansible.run_module import RunAnsibleModule, RunShellCommand
from .commands.fab import Fab
from .commands.inventory_lookup.inventory_lookup import Lookup, Ssh, Mosh, DjangoManage
from commcare_cloud.commands.command_base import CommandBase
from .environment.paths import (
    get_available_envs,
    get_virtualenv_path,
)
from six.moves import shlex_quote

COMMAND_TYPES = [
    AnsiblePlaybook,
    DeployStack,
    UpdateConfig,
    AfterReboot,
    RestartElasticsearch,
    BootstrapUsers,
    UpdateUsers,
    RunShellCommand,
    RunAnsibleModule,
    Fab,
    Lookup,
    Ssh,
    Mosh,
    DjangoManage,
    Service,
    ValidateEnvironmentSettings,
]


def run_on_control_instead(args, sys_argv):
    argv = [arg for arg in sys_argv][1:]
    argv.remove('--control')
    executable = 'commcare-cloud'
    cmd_parts = [
        executable, args.env_name, 'ssh', 'control',
        'source ~/init-ansible && git checkout master && control/update_code.sh && source ~/init-ansible && {} {}'
        .format(executable, ' '.join([shlex_quote(arg) for arg in argv]))
    ]

    print_command(' '.join([shlex_quote(part) for part in cmd_parts]))
    os.execvp(executable, cmd_parts)


def add_backwards_compatibility_to_args(args):
    """
    make accessing args.environment trigger a DeprecationWarning and return args.env_name

    This function and any calls to it may be deleted once all open PRs using args.environment
    have been merged and all such usage fixed.
    """
    class NamespaceWrapper(args.__class__):
        @property
        def environment(self):
            warnings.warn("args.environment is deprecated. Use args.env_name instead.",
                          DeprecationWarning)
            return self.env_name

    args.__class__ = NamespaceWrapper


def main():
    os.environ['PATH'] = '{}:{}'.format(get_virtualenv_path(), os.environ['PATH'])
    parser = ArgumentParser()
    available_envs = get_available_envs()
    parser.add_argument('env_name', choices=available_envs, metavar='environment', help=(
        "server environment to run against"
    ))
    parser.add_argument('--control', action='store_true', help=(
        "include to run command remotely on the control machine"
    ))
    subparsers = parser.add_subparsers(dest='command')

    commands = {}

    for command_type in COMMAND_TYPES:
        assert issubclass(command_type, CommandBase), command_type
        cmd = command_type(subparsers.add_parser(
            command_type.command, help=command_type.help, aliases=command_type.aliases))
        cmd.make_parser()
        commands[cmd.command] = cmd
        for alias in cmd.aliases:
            commands[alias] = cmd

    args, unknown_args = parser.parse_known_args()

    add_backwards_compatibility_to_args(args)

    if args.control:
        run_on_control_instead(args, sys.argv)
    exit_code = commands[args.command].run(args, unknown_args)
    if exit_code is not 0:
        exit(exit_code)


if __name__ == '__main__':
    main()
