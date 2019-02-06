# coding: utf-8
import os
import subprocess
from six.moves import shlex_quote
from clint.textui import puts, colored
from commcare_cloud.cli_utils import ask, print_command
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext,
    DEPRECATED_ANSIBLE_ARGS,
    get_common_ssh_args,
    get_user_arg, run_action_with_check_mode)
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment
from commcare_cloud.parse_help import add_to_help_text, filtered_help_message
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
                below_line='Options:',
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
                args.become, args.become_user, args.use_factory_auth,
                *unknown_args
            )

        def run_check():
            return _run_ansible(args, '--check', *unknown_args)

        def run_apply():
            return _run_ansible(args, *unknown_args)

        return run_action_with_check_mode(run_check, run_apply, args.skip_check, args.quiet)


def run_ansible_module(environment, ansible_context, inventory_group, module, module_args,
                       become, become_user, factory_auth, *extra_args):
    cmd_parts = (
        'ansible', inventory_group,
        '-m', module,
        '-i', environment.paths.inventory_source,
        '-a', module_args,
        '--diff',
    ) + tuple(extra_args)

    environment.create_generated_yml()
    public_vars = environment.public_vars
    cmd_parts += get_user_arg(public_vars, extra_args, use_factory_auth=factory_auth)
    become = become or bool(become_user)
    become_user = become_user
    include_vars = False
    if become:
        cmd_parts += ('--become',)
        include_vars = True
        if become_user:
            cmd_parts += ('--become-user', become_user)

    if include_vars:
        cmd_parts += (
            '-e', '@{}'.format(environment.paths.vault_yml),
            '-e', '@{}'.format(environment.paths.public_yml),
            '-e', '@{}'.format(environment.paths.generated_yml),
        )

    ask_vault_pass = include_vars and public_vars.get('commcare_cloud_use_vault', True)
    if ask_vault_pass:
        cmd_parts += ('--vault-password-file={}/echo_vault_password.sh'.format(ANSIBLE_DIR),)
    cmd_parts_with_common_ssh_args = get_common_ssh_args(environment, use_factory_auth=factory_auth)
    cmd_parts += cmd_parts_with_common_ssh_args
    cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
    print_command(cmd)
    env_vars = ansible_context.env_vars
    if ask_vault_pass:
        env_vars['ANSIBLE_VAULT_PASSWORD'] = environment.get_ansible_vault_password()
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
            puts(colored.yellow(
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
    )

    def run(self, args, unknown_args):
        args.module = 'datadog_event'
        environment = get_environment(args.env_name)
        vault = environment.get_vault_variables()['secrets']
        tags = "environment:{}".format(args.env_name)
        args.module_args = "api_key={api_key} app_key={app_key} " \
            "tags='{tags}' text='{text}' title='{title}'".format(
                api_key=vault['DATADOG_API_KEY'],
                app_key=vault['DATADOG_APP_KEY'],
                tags=tags,
                text=args.event_text,
                title=args.event_title
            )
        env_vars = AnsibleContext(args).env_vars
        cmd_parts = (
            'ansible', '127.0.0.1',
            '-m', args.module,
            '-i', environment.paths.inventory_source,
            '-a', args.module_args,
            '--diff',
        )
        return subprocess.call(cmd_parts, env=env_vars)


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
