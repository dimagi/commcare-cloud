# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import
import os
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
]


def main():
    os.environ['PATH'] = '{}:{}'.format(get_virtualenv_path(), os.environ['PATH'])
    parser = ArgumentParser()
    available_envs = get_available_envs()
    parser.add_argument('environment', choices=available_envs, help=(
        "server environment to run against"
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
    exit_code = commands[args.command].run(args, unknown_args)
    if exit_code is not 0:
        exit(exit_code)

if __name__ == '__main__':
    main()
