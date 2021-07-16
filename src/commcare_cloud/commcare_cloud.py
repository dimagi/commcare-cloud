# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import

from __future__ import unicode_literals
import inspect
import os
import sys
from collections import OrderedDict
from textwrap import dedent

from clint.textui import puts

from commcare_cloud.cli_utils import print_command
from commcare_cloud.colors import color_error
from commcare_cloud.commands.ansible.downtime import Downtime
from commcare_cloud.commands.deploy.command import Deploy
from commcare_cloud.commands.migrations.couchdb import MigrateCouchdb
from commcare_cloud.commands.migrations.copy_files import CopyFiles
from commcare_cloud.commands.secrets import Secrets, MigrateSecrets
from commcare_cloud.commands.sentry import ExportSentryEvents
from commcare_cloud.commands.terraform.aws import AwsList, AwsFillInventory, AwsSignIn
from commcare_cloud.commands.terraform.openvpn import OpenvpnActivateUser, OpenvpnClaimUser
from commcare_cloud.commands.terraform.terraform import Terraform
from commcare_cloud.commands.terraform.terraform_migrate_state import TerraformMigrateState
from commcare_cloud.commands.validate_environment_settings import ValidateEnvironmentSettings
from .argparse14 import ArgumentParser, RawTextHelpFormatter

from .commands.ansible.ansible_playbook import (
    AnsiblePlaybook,
    UpdateConfig, AfterReboot, BootstrapUsers, DeployStack,
    UpdateUsers, UpdateUserPublicKey, UpdateSupervisorConfs,
)
from commcare_cloud.commands.ansible.service import Service
from .commands.ansible.run_module import RunAnsibleModule, RunShellCommand, Ping, SendDatadogEvent
from .commands.fab import Fab
from .commands.inventory_lookup.inventory_lookup import Lookup, Ssh, Mosh, DjangoManage, Tmux, ForwardPort
from .commands.ansible.ops_tool import ListDatabases, CeleryResourceReport, PillowResourceReport, \
    CouchDBClusterInfo, UpdateLocalKnownHosts, PillowTopicAssignments
from commcare_cloud.commands.command_base import CommandBase, Argument, CommandError
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
        SendDatadogEvent,
        DjangoManage,
        Tmux,
        ExportSentryEvents,
        PillowTopicAssignments,
    ]),
    ('operational', [
        Secrets,
        MigrateSecrets,
        Ping,
        AnsiblePlaybook,
        DeployStack,
        UpdateConfig,
        AfterReboot,
        BootstrapUsers,
        UpdateUsers,
        UpdateUserPublicKey,
        UpdateSupervisorConfs,
        Fab,
        Deploy,
        Service,
        MigrateCouchdb,
        Downtime,
        CopyFiles,
        ListDatabases,
        CeleryResourceReport,
        PillowResourceReport,
        CouchDBClusterInfo,
        Terraform,
        TerraformMigrateState,
        AwsSignIn,
        AwsList,
        AwsFillInventory,
        OpenvpnActivateUser,
        OpenvpnClaimUser,
        ForwardPort,
    ])
])

COMMAND_TYPES = sorted(
    [cmd for group in COMMAND_GROUPS.values() for cmd in group],
    key=lambda cmd: cmd.command,
)


def run_on_control_instead(args, sys_argv):
    argv = sys_argv[1:]
    argv.remove('--control')
    executable = 'commcare-cloud'
    branch = getattr(args, 'branch', 'master')
    default_virtualenv = "ansible" if sys.version_info[0] == 2 else "cchq"
    venv = os.environ.get("CCHQ_VIRTUALENV", default_virtualenv)
    cmd_parts = [
        executable, args.env_name, 'ssh', 'control[0]', '-t',
        '{env}cd ~/commcare-cloud && git fetch --prune && git checkout {branch} '
        '&& git reset --hard origin/{branch} && source ~/init-ansible && {cchq} {cchq_args}'
        .format(
            env=('export CCHQ_VIRTUALENV=%s; ' % venv if venv else ''),
            branch=branch,
            cchq=executable,
            cchq_args=' '.join(shlex_quote(arg) for arg in argv),
        )
    ]

    print_command(' '.join([shlex_quote(part) for part in cmd_parts]))
    os.execvp(executable, cmd_parts)


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


def call_commcare_cloud(input_argv=sys.argv):
    # throw error if user is attempting to use python 2
    if not os.environ.get("TRAVIS_TEST") and sys.version_info[0] == 2:
        exit(dedent("""
            Error: you must upgrade to Python 3. Python 2 is no longer supported.

            To setup Python 3.6, see
            https://dimagi.github.io/commcare-cloud/setup/installation.html
            """))

    put_virtualenv_bin_on_the_path()
    parser, subparsers, commands = make_command_parser(available_envs=get_available_envs())

    raw_args = input_argv[1:]
    if not raw_args:
        parser.print_help()
        return

    args, unknown_args = parser.parse_known_args(raw_args)

    if args.control:
        run_on_control_instead(args, input_argv)

    try:
        exit_code = commands[args.command].run(args, unknown_args)
    except CommandError as e:
        puts(color_error(str(e), bold=True))
        return 1

    return exit_code


def main():
    exit_code = call_commcare_cloud()
    if exit_code != 0:
        exit(exit_code)


if __name__ == '__main__':
    main()
