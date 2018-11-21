from __future__ import absolute_import

from commcare_cloud.manage_commcare_cloud.test_environments import TestEnvironments
from ..argparse14 import ArgumentParser

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.manage_commcare_cloud.configure import Configure
from commcare_cloud.manage_commcare_cloud.get import Get
from commcare_cloud.manage_commcare_cloud.list_vault_keys import ListVaultKeys
from commcare_cloud.manage_commcare_cloud.install import Install
from commcare_cloud.manage_commcare_cloud.make_docs import MakeDocs
from commcare_cloud.manage_commcare_cloud.make_changelog import MakeChangelogIndex, \
    MakeChangelog

COMMAND_TYPES = [
    Configure,
    Get,
    Install,
    ListVaultKeys,
    MakeChangelog,
    MakeChangelogIndex,
    MakeDocs,
    TestEnvironments,
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
