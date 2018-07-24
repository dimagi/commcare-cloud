# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import

import inspect
import os

import sys
import re
import warnings
from collections import OrderedDict

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.ansible.downtime import Downtime
from commcare_cloud.commands.migrations.couchdb import MigrateCouchdb
from commcare_cloud.commands.migrations.copy_files import CopyFiles
from commcare_cloud.commands.validate_environment_settings import ValidateEnvironmentSettings
from .argparse14 import ArgumentParser, RawTextHelpFormatter

from .commands.ansible.ansible_playbook import (
    AnsiblePlaybook,
    UpdateConfig, AfterReboot, RestartElasticsearch, BootstrapUsers, DeployStack,
    UpdateUsers, UpdateSupervisorConfs, UpdateLocalKnownHosts,
)
from commcare_cloud.commands.ansible.service import Service
from .commands.ansible.run_module import RunAnsibleModule, RunShellCommand, Ping
from .commands.fab import Fab
from .commands.inventory_lookup.inventory_lookup import Lookup, Ssh, Mosh, DjangoManage, Tmux
from commcare_cloud.commands.command_base import CommandBase, Argument
from .environment.paths import (
    get_available_envs,
    put_virtualenv_bin_on_the_path,
)
from six.moves import shlex_quote

COMMAND_GROUPS = OrderedDict([
    ('housekeeping', [
        ValidateEnvironmentSettings,
        UpdateLocalKnownHosts,
    ]),
    ('ad-hoc', [
        Lookup,
        Ssh,
        Mosh,
        RunAnsibleModule,
        RunShellCommand,
        DjangoManage,
        Tmux,
    ]),
    ('operational', [
        Ping,
        AnsiblePlaybook,
        DeployStack,
        UpdateConfig,
        AfterReboot,
        RestartElasticsearch,
        BootstrapUsers,
        UpdateUsers,
        UpdateSupervisorConfs,
        Fab,
        Service,
        MigrateCouchdb,
        Downtime,
        CopyFiles,
    ])
])

COMMAND_TYPES = [command_type for command_types in COMMAND_GROUPS.values()
                 for command_type in command_types]


def run_on_control_instead(args, sys_argv):
    argv = [arg for arg in sys_argv][1:]
    argv.remove('--control')
    executable = 'commcare-cloud'
    cmd_parts = [
        executable, args.env_name, 'ssh', 'control', '-t',
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


def make_command_parser(available_envs, formatter_class=RawTextHelpFormatter,
                        subparser_formatter_class=None, prog=None, add_help=True, for_docs=False):
    if subparser_formatter_class is None:
        subparser_formatter_class = formatter_class
    parser = ArgumentParser(formatter_class=formatter_class, prog=prog, add_help=add_help)
    if available_envs:
        env_name_kwargs = dict(choices=available_envs)
    else:
        env_name_kwargs = dict(metavar='<env>')
    parser.add_argument('env_name', help=(
        "server environment to run against"
    ), **env_name_kwargs)
    Argument('--control', action='store_true', help="""
        Run command remotely on the control machine.

        You can add `--control` _directly after_ `commcare-cloud` to any command
        in order to run the command not from the local machine
        using the local code,
        but from from the control machine for that environment,
        using the latest version of `commcare-cloud` available.

        It works by issuing a command to ssh into the control machine,
        update the code, and run the same command entered locally but with
        `--control` removed. For long-running commands,
        you will have to remain connected to the the control machine
        for the entirety of the run.
    """).add_to_parser(parser)
    subparsers = parser.add_subparsers(dest='command')

    commands = {}

    for command_type in COMMAND_TYPES:
        assert issubclass(command_type, CommandBase), command_type
        cmd = command_type(subparsers.add_parser(
            command_type.command,
            help=inspect.cleandoc(command_type.help).splitlines()[0],
            aliases=command_type.aliases,
            description=inspect.cleandoc(command_type.help),
            formatter_class=subparser_formatter_class,
            add_help=add_help)
        )
        cmd.make_parser(for_docs=for_docs)
        commands[cmd.command] = cmd
        for alias in cmd.aliases:
            commands[alias] = cmd
    return parser, subparsers, commands


def make_changelog_parser():
    # Parse the contents of the changelog dir
    changelog_contents = []
    files_to_ignore = ['0000-changelog.md', 'index.md']
    changelog_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'docs', 'changelog')
    sorted_files = _sort_files(changelog_dir)
    for change_file_name in sorted_files:
        if change_file_name not in files_to_ignore:
            try:
                with open(os.path.join(changelog_dir, change_file_name)) as change_file:
                    change_context = ''
                    change_date = ''
                    in_change_context = False
                    change_action_required = False
                    reached_details_line = False
                    for line_number, line in enumerate(change_file):
                        if line_number == 0:
                            change_summary = re.search('(?<=\.).*', line).group().strip()
                        if '**Date:**' in line:
                            change_date = line.split('**Date:**')[1].strip()
                        if '**Optional per env:**' in line:
                            option = line.split('**Optional per env:**')[1].strip().lower()
                            if "no" in option:
                                change_action_required = True
                        if '## Details' in line:
                            in_change_context = False
                            reached_details_line = True
                        if in_change_context:
                            change_context += line.replace('\n', '')
                        if '## Change Context' in line:
                            in_change_context = True
                    assert change_file_name and change_context and change_date and change_summary and\
                           change_action_required and reached_details_line
                    this_changelog = {'filename': change_file_name,
                                      'context': change_context,
                                      'date': change_date,
                                      'summary': change_summary,
                                      'action_required': change_action_required}

                changelog_contents.append(this_changelog)
            except (AttributeError, AssertionError):
                print("Error parsing the file {}.".format(change_file_name))
                sys.exit(1)
    return changelog_contents


def _sort_files(directory):
    """
    Sorts filenames by descending alphanumeric order, userful for organizing the changelog index.md
    """
    def _natural_keys(text):
        retval = [int(c) if c.isdigit() else c for c in text[:4]]
        return retval
    unsorted_files = os.listdir(directory)
    unsorted_files.sort(key=_natural_keys, reverse=True)
    return unsorted_files


def main():
    put_virtualenv_bin_on_the_path()
    parser, subparsers, commands = make_command_parser(available_envs=get_available_envs())
    args, unknown_args = parser.parse_known_args()

    add_backwards_compatibility_to_args(args)

    if args.control:
        run_on_control_instead(args, sys.argv)
    exit_code = commands[args.command].run(args, unknown_args)
    if exit_code is not 0:
        exit(exit_code)


if __name__ == '__main__':
    main()
