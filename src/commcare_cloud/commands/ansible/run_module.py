# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import subprocess
from six.moves import shlex_quote
from clint.textui import puts
from commcare_cloud.cli_utils import ask, print_command
from commcare_cloud.colors import color_notice
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext,
    DEPRECATED_ANSIBLE_ARGS,
    get_common_ssh_args,
    get_user_arg, run_action_with_check_mode)
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment
from commcare_cloud.parse_help import add_to_help_text, filtered_help_message, ANSIBLE_HELP_OPTIONS_PREFIX
from commcare_cloud.environment.paths import ANSIBLE_DIR

NON_POSITIONAL_ARGUMENTS = (
    Argument('-b', '--become', action='store_true', help=(
        "run operations with become (implies vault password prompting if necessary)"
    ), include_in_docs=False),
    Argument('--become-user', help=(
        "run operations as this user (default=root)"
    ), include_in_docs=False),
    shared_args.SKIP_CHECK_ARG,
    shared_args.FACTORY_AUTH_ARG,
    shared_args.QUIET_ARG,
    shared_args.STDOUT_CALLBACK_ARG,
)


class RunAnsibleModule(CommandBase):
    command = 'run-module'
    help = """
    Run an arbitrary Ansible module.

    Example:

    To print out the `inventory_hostname` ansible variable for each machine, run
    ```
    commcare-cloud <env> run-module all debug "msg={{ inventory_hostname }}"
    ```
    """
    arguments = (
        shared_args.INVENTORY_GROUP_ARG,
        Argument('module', help="""
            The name of the ansible module to run. Complete list of built-in modules
            can be found at [Module Index](http://docs.ansible.com/ansible/latest/modules/modules_by_category.html).
        """),
        Argument('module_args', help="""
            Args for the module, formatted as a single string.
            (Tip: put quotes around it, as it will likely contain spaces.)
            Both `arg1=value1 arg2=value2` syntax
            and `{"arg1": "value1", "arg2": "value2"}` syntax are accepted.
        """),
    ) + NON_POSITIONAL_ARGUMENTS

    def modify_parser(self):
        add_to_help_text(self.parser, "\n{}\n{}".format(
            "The ansible options below are available as well:",
            filtered_help_message(
                "ansible -h",
                below_line=ANSIBLE_HELP_OPTIONS_PREFIX,
                above_line='Some modules do not make sense in Ad-Hoc (include, meta, etc)',
                exclude_args=DEPRECATED_ANSIBLE_ARGS + [
                    '--help',
                    '--become',
                    '--become-user',
                    '-i',
                    '-m',
                    '-a',
                    '--ask-vault-pass',
                    '--vault-password-file',
                    '--check',
                    '--diff'
                ],
            )
        ))

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()
        ansible_context = AnsibleContext(args)

        def _run_ansible(args, *unknown_args):
            return run_ansible_module(
                environment, ansible_context,
                args.inventory_group, args.module, args.module_args,
                become=args.become, become_user=args.become_user,
                use_factory_auth=args.use_factory_auth, extra_args=unknown_args
            )

        def run_check():
            with environment.secrets_backend.suppress_datadog_event():
                return _run_ansible(args, '--check', *unknown_args)

        def run_apply():
            return _run_ansible(args, *unknown_args)

        return run_action_with_check_mode(run_check, run_apply, args.skip_check, args.quiet)


def run_ansible_module(environment, ansible_context, inventory_group, module, module_args,
                       become=True, become_user=None, use_factory_auth=False, quiet=False, extra_args=()):
    extra_args = tuple(extra_args)
    if not quiet:
        extra_args = ("--diff",) + extra_args
    else:
        extra_args = ("--one-line",) + extra_args

    cmd_parts = (
        'ansible', inventory_group,
        '-m', module,
        '-i', environment.paths.inventory_source,
        '-a', module_args,
    ) + extra_args

    environment.create_generated_yml()
    public_vars = environment.public_vars
    cmd_parts += get_user_arg(public_vars, extra_args, use_factory_auth=use_factory_auth)
    become = become or bool(become_user)
    become_user = become_user
    needs_secrets = False
    env_vars = ansible_context.env_vars

    if become:
        cmd_parts += ('--become',)
        needs_secrets = True
        if become_user:
            cmd_parts += ('--become-user', become_user)

    if needs_secrets:
        cmd_parts += (
            '-e', '@{}'.format(environment.paths.public_yml),
            '-e', '@{}'.format(environment.paths.generated_yml),
        )
        cmd_parts += environment.secrets_backend.get_extra_ansible_args()
        env_vars.update(environment.secrets_backend.get_extra_ansible_env_vars())

    cmd_parts_with_common_ssh_args = get_common_ssh_args(environment, use_factory_auth=use_factory_auth)
    cmd_parts += cmd_parts_with_common_ssh_args
    cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
    if not quiet:
        print_command(cmd)
    return subprocess.call(cmd_parts, env=env_vars)


class RunShellCommand(CommandBase):
    command = 'run-shell-command'
    help = """
    Run an arbitrary command via the Ansible shell module.

    Example:

    ```
    commcare-cloud <env> run-shell-command all 'df -h | grep /opt/data'
    ```

    to get disk usage stats for `/opt/data` on every machine.
    """

    skip_setup_on_control_by_default = True

    arguments = (
        shared_args.INVENTORY_GROUP_ARG,
        Argument('shell_command', help="""
            Command to run remotely.
            (Tip: put quotes around it, as it will likely contain spaces.)
            Cannot being with `sudo`; to do that use the ansible `--become` option.
        """),
        Argument('--silence-warnings', action='store_true',
                 help="Silence shell warnings (such as to use another module instead)."),
    ) + NON_POSITIONAL_ARGUMENTS

    def modify_parser(self):
        RunAnsibleModule(self.parser).modify_parser()

    def run(self, args, unknown_args):
        if args.shell_command.strip().startswith('sudo '):
            puts(color_notice(
                "To run as another user use `--become` (for root) or `--become-user <user>`.\n"
                "Using 'sudo' directly in the command is non-standard practice."))
            if not ask("Do you know what you're doing and want to run this anyway?", quiet=args.quiet):
                return 0  # exit code

        args.module = 'shell'
        if args.silence_warnings:
            args.module_args = 'warn=false ' + args.shell_command
        else:
            args.module_args = args.shell_command
        args.skip_check = True
        args.quiet = True
        del args.shell_command
        return RunAnsibleModule(self.parser).run(args, unknown_args)


class SendDatadogEvent(CommandBase):
    command = 'send-datadog-event'
    help = "Track an infrastructure maintainance event in Datadog"

    arguments = (
        Argument('event_title', help="""
            Title of the datadog event.
        """),
        Argument('event_text', help="""
            Text content of the datadog event.
        """),
        Argument('--tags', nargs="*", help="""
            Additional tags e.g. host:web2
        """),
        Argument('--alert_type', choices=["error", "warning", "info", "success"], default="info", help="""
            Alert type.
        """),
    )

    def run(self, args, unknown_args):
        args.module = 'datadog_event'
        environment = get_environment(args.env_name)
        datadog_api_key = environment.get_secret('DATADOG_API_KEY')
        datadog_app_key = environment.get_secret('DATADOG_APP_KEY')
        tags = args.tags or []
        tags.append("environment:{}".format(args.env_name))
        args.module_args = "api_key={api_key} app_key={app_key} " \
            "tags='{tags}' text='{text}' title='{title}' aggregation_key={agg}".format(
                api_key=datadog_api_key,
                app_key=datadog_app_key,
                tags=",".join(tags),
                text=args.event_text,
                title=args.event_title,
                agg='commcare-cloud'
            )
        return run_ansible_module(
            environment, AnsibleContext(args),
            '127.0.0.1', args.module, args.module_args,
            become=False, quiet=True
        )


class Ping(CommandBase):
    command = 'ping'
    help = 'Ping specified or all machines to see if they have been provisioned yet.'

    arguments = (
        shared_args.INVENTORY_GROUP_ARG,
    ) + NON_POSITIONAL_ARGUMENTS

    def run(self, args, unknown_args):
        args.shell_command = 'echo {{ inventory_hostname }}'
        args.silence_warnings = False
        return RunShellCommand(self.parser).run(args, unknown_args)
