# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import
import os
from argparse import ArgumentParser

from commcare_cloud.commands.ansible.ansible_playbook import AnsiblePlaybook, \
    UpdateConfig, AfterReboot, RestartElasticsearch, BootstrapUsers
from commcare_cloud.commands.ansible.run_module import RunAnsibleModule, RunShellCommand
from commcare_cloud.commands.fab import Fab
from commcare_cloud.commands.inventory_lookup import Lookup, Ssh, Mosh
from .environment import (
    get_available_envs,
    get_virtualenv_path,
)


STANDARD_ARGS = [
    AnsiblePlaybook,
    UpdateConfig,
    AfterReboot,
    RestartElasticsearch,
    BootstrapUsers,
    RunShellCommand,
    RunAnsibleModule,
    Fab,
    Lookup,
    Ssh,
    Mosh,
]


def main():
    os.environ['PATH'] = '{}:{}'.format(get_virtualenv_path(), os.environ['PATH'])
    parser = ArgumentParser()
    available_envs = get_available_envs()
    parser.add_argument('environment', choices=available_envs, help=(
        "server environment to run against"
    ))
    subparsers = parser.add_subparsers(dest='command')

    for standard_arg in STANDARD_ARGS:
        standard_arg.make_parser(subparsers.add_parser(standard_arg.command, help=standard_arg.help))

    args, unknown_args = parser.parse_known_args()
    for standard_arg in STANDARD_ARGS:
        if args.command == standard_arg.command:
            standard_arg.run(args, unknown_args)

if __name__ == '__main__':
    main()
