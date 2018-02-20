# coding: utf-8
import os
import subprocess
from six.moves import shlex_quote
from clint.textui import puts, colored
from commcare_cloud.cli_utils import ask, print_command
from commcare_cloud.commands.ansible.helpers import AnsibleContext, DEPRECATED_ANSIBLE_ARGS, \
    get_common_ssh_args
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commands.shared_args import arg_inventory_group, arg_skip_check, arg_quiet, \
    arg_stdout_callback
from commcare_cloud.parse_help import add_to_help_text, filtered_help_message
from commcare_cloud.environment import ANSIBLE_DIR, get_inventory_filepath, get_vault_vars_filepath, \
    get_public_vars_filepath, get_public_vars


class RunAnsibleModule(CommandBase):
    command = 'run-module'
    help = (
        'Run an arbitrary Ansible module.'
    )

    def make_parser(self):
        arg_inventory_group(self.parser)
        self.parser.add_argument('module', help="The module to run")
        self.parser.add_argument('module_args', help="The arguments to pass to the module")
        self.add_non_positional_arguments()

    def add_non_positional_arguments(self):
        self.parser.add_argument('-u', '--user', dest='remote_user', default='ansible', help=(
            "connect as this user (default=ansible)"
        ))
        self.parser.add_argument('-b', '--become', action='store_true', help=(
            "run operations with become (implies vault password prompting if necessary)"
        ))
        self.parser.add_argument('--become-user', help=(
            "run operations as this user (default=root)"
        ))
        arg_skip_check(self.parser)
        arg_quiet(self.parser)
        arg_stdout_callback(self.parser)
        add_to_help_text(self.parser, "\n{}\n{}".format(
            "The ansible options below are available as well",
            filtered_help_message(
                "ansible -h",
                below_line='Options:',
                above_line='Some modules do not make sense in Ad-Hoc (include, meta, etc)',
                exclude_args=DEPRECATED_ANSIBLE_ARGS + [
                    '--help',
                    '--user',
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
        ansible_context = AnsibleContext(args)
        public_vars = get_public_vars(args.environment)

        def _run_ansible(args, *unknown_args):
            cmd_parts = (
                'ANSIBLE_CONFIG={}'.format(os.path.join(ANSIBLE_DIR, 'ansible.cfg')),
                'ansible', args.inventory_group,
                '-m', args.module,
                '-i', get_inventory_filepath(args.environment),
                '-u', args.remote_user,
                '-a', args.module_args,
                '--diff',
            ) + tuple(unknown_args)

            become = args.become or bool(args.become_user)
            become_user = args.become_user
            include_vars = False
            if become:
                if become_user not in ('cchq',):
                    # ansible user can do things as cchq without a password,
                    # but needs the ansible user password in order to do things as other users.
                    # In that case, we need to pull in the vault variable containing this password
                    include_vars = True
                if become_user:
                    cmd_parts += ('--become-user', args.become_user)
                else:
                    cmd_parts += ('--become',)

            if include_vars:
                cmd_parts += (
                    '-e', '@{}'.format(get_vault_vars_filepath(args.environment)),
                    '-e', '@{}'.format(get_public_vars_filepath(args.environment)),
                )

            ask_vault_pass = include_vars and public_vars.get('commcare_cloud_use_vault', True)
            if ask_vault_pass:
                cmd_parts += ('--vault-password-file=/bin/cat',)

            cmd_parts += get_common_ssh_args(public_vars)
            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print_command(cmd)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True, env=ansible_context.env_vars)
            if ask_vault_pass:
                p.communicate(input='{}\n'.format(ansible_context.get_ansible_vault_password()))
            else:
                p.communicate()
            return p.returncode

        def run_check():
            return _run_ansible(args, '--check', *unknown_args)

        def run_apply():
            return _run_ansible(args, *unknown_args)

        exit_code = 0

        if args.skip_check:
            user_wants_to_apply = ask('Do you want to apply without running the check first?',
                                      quiet=args.quiet)
        else:
            exit_code = run_check()
            if exit_code == 1:
                # this means there was an error before ansible was able to start running
                exit(exit_code)
                return  # for IDE
            elif exit_code == 0:
                puts(colored.green(u"✓ Check completed with status code {}".format(exit_code)))
                user_wants_to_apply = ask('Do you want to apply these changes?',
                                          quiet=args.quiet)
            else:
                puts(colored.red(u"✗ Check failed with status code {}".format(exit_code)))
                user_wants_to_apply = ask('Do you want to try to apply these changes anyway?',
                                          quiet=args.quiet)

        if user_wants_to_apply:
            exit_code = run_apply()
            if exit_code == 0:
                puts(colored.green(u"✓ Apply completed with status code {}".format(exit_code)))
            else:
                puts(colored.red(u"✗ Apply failed with status code {}".format(exit_code)))

        exit(exit_code)


class RunShellCommand(CommandBase):
    command = 'run-shell-command'
    help = 'Run an arbitrary command via the shell module.'

    def make_parser(self):
        arg_inventory_group(self.parser)
        self.parser.add_argument('shell_command', help="The shell command you want to run")
        RunAnsibleModule(self.parser).add_non_positional_arguments()

    def run(self, args, unknown_args):
        if args.shell_command.strip().startswith('sudo '):
            puts(colored.yellow(
                "To run as another user use `--become` (for root) or `--become-user <user>`.\n"
                "Using 'sudo' directly in the command is non-standard practice."))
            if not ask("Do you know what you're doing and want to run this anyway?", quiet=args.quiet):
                exit(0)

        args.module = 'shell'
        args.module_args = args.shell_command
        args.skip_check = True
        args.quiet = True
        del args.shell_command
        RunAnsibleModule(self.parser).run(args, unknown_args)
