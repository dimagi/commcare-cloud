# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import
import getpass
import os
import re
import sys
from six.moves import input, shlex_quote
from argparse import ArgumentParser
import subprocess
from clint.textui import puts, colored
import yaml

from .getinventory import get_server_address
from .parse_help import filtered_help_message, add_to_help_text
from .paths import (
    ANSIBLE_DIR,
    ENVIRONMENTS_DIR,
    FABFILE,
    get_inventory_filepath,
    get_public_vars_filepath,
    get_vault_vars_filepath,
    REPO_BASE,
)


DEPRECATED_ANSIBLE_ARGS = [
    '--sudo',
    '--sudo-user',
    '--su',
    '--su-user',
    '--ask-sudo-pass',
    '--ask-su-pass',
]


def ask(message, strict=False, quiet=False):
    if quiet:
        return True
    yesno = 'YES/NO' if strict else 'y/N'
    negatives = ('NO', 'N', 'n', 'no')
    affirmatives = ('YES',) if strict else ('y', 'Y', 'yes')
    acceptable_options = affirmatives + negatives

    r = input('{} [{}]'.format(message, yesno))
    while r not in acceptable_options:
        r = input('{} or {}? '.format(*yesno.split('/')))
    return r in affirmatives


def arg_skip_check(parser):
    parser.add_argument('--skip-check', action='store_true', default=False, help=(
        "skip the default of viewing --check output first"
    ))


def arg_quiet(parser):
    parser.add_argument('--quiet', action='store_true', default=False, help=(
        "skip all user prompts and proceed as if answered in the affirmative"
    ))


def arg_branch(parser):
    parser.add_argument('--branch', default='master', help=(
        "the name of the commcarehq-ansible git branch to run against, if not master"
    ))


def arg_stdout_callback(parser):
    default = os.environ.get('ANSIBLE_STDOUT_CALLBACK') or 'default'
    parser.add_argument(
        '--output', dest='stdout_callback', default=default, choices=['actionable', 'minimal'],
        help=("The callback plugin to use for generating output. "
              "See ansible-doc -t callback -l and ansible-doc -t callback [ansible|minimal]"
    ))


def get_public_vars(environment):
    filename = get_public_vars_filepath(environment)
    with open(filename) as f:
        return yaml.load(f)


def get_common_ssh_args(public_vars):
    pem = public_vars.get('commcare_cloud_pem', None)
    strict_host_key_checking = public_vars.get('commcare_cloud_strict_host_key_checking', True)

    common_ssh_args = []
    if pem:
        common_ssh_args.extend(['-i', pem])
    if not strict_host_key_checking:
        common_ssh_args.append('-o StrictHostKeyChecking=no')

    cmd_parts = tuple()
    if common_ssh_args:
        cmd_parts += ('--ssh-common-args', ' '.join(shlex_quote(arg) for arg in common_ssh_args))
    return cmd_parts


def has_arg(unknown_args, short_form, long_form):
    """
    check whether a conceptual arg is present in a list of command line tokens

    :param unknown_args: list of command line tokens
    :param short_form: dash followed by single letter, e.g. '-f'
    :param long_form: double dash followed by work, e.g. '--forks'
    :return: boolean
    """

    assert re.match(r'^-[a-zA-Z0-9]$', short_form)
    assert re.match(r'^--\w+$', long_form)
    if long_form in unknown_args:
        return True
    for arg in unknown_args:
        if arg.startswith(short_form):
            return True
    return False


class AnsibleContext(object):
    def __init__(self, args):
        self._ansible_vault_password = None
        self.env_vars = self._build_env(args)

    def get_ansible_vault_password(self):
        if self._ansible_vault_password is None:
            self._ansible_vault_password = getpass.getpass("Vault Password: ")
        return self._ansible_vault_password

    def _build_env(self, args):
        """Look for args that have been flagged as environment variables
        and add them to the env dict with appropriate naming
        """
        env = os.environ.copy()
        env['ANSIBLE_CONFIG'] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
        if hasattr(args, 'stdout_callback'):
            env['ANSIBLE_STDOUT_CALLBACK'] = args.stdout_callback
        return env


class AnsiblePlaybook(object):
    command = 'ansible-playbook'
    help = (
        "Run a playbook as you would with ansible-playbook, "
        "but with boilerplate settings already set based on your <environment>. "
        "By default, you will see --check output and then asked whether to apply. "
    )

    @staticmethod
    def make_parser(parser):
        arg_skip_check(parser)
        arg_quiet(parser)
        arg_branch(parser)
        arg_stdout_callback(parser)
        parser.add_argument('playbook', help=(
            "The ansible playbook .yml file to run."
        ))
        add_to_help_text(parser, "\n{}\n{}".format(
            "The ansible-playbook options below are available as well",
            filtered_help_message(
                "ansible-playbook -h",
                below_line='Options:',
                above_line=None,
                exclude_args=DEPRECATED_ANSIBLE_ARGS + [
                    '--help',
                    '--diff',
                    '--check',
                    '-i',
                    '--ask-vault-pass',
                    '--vault-password-file',
                ],
            )
        ))

    @staticmethod
    def run(args, unknown_args):
        ansible_context = AnsibleContext(args)
        check_branch(args)
        public_vars = get_public_vars(args.environment)
        ask_vault_pass = public_vars.get('commcare_cloud_use_vault', True)

        def ansible_playbook(environment, playbook, *cmd_args):
            cmd_parts = (
                'ansible-playbook',
                os.path.join(ANSIBLE_DIR, '{playbook}'.format(playbook=playbook)),
                '-i', get_inventory_filepath(environment),
                '-e', '@{}'.format(get_vault_vars_filepath(environment)),
                '-e', '@{}'.format(get_public_vars_filepath(environment)),
                '--diff',
            ) + cmd_args

            if not has_arg(unknown_args, '-u', '--user'):
                cmd_parts += ('-u', 'ansible')

            if not has_arg(unknown_args, '-f', '--forks'):
                cmd_parts += ('--forks', '15')

            if has_arg(unknown_args, '-D', '--diff') or has_arg(unknown_args, '-C', '--check'):
                puts(colored.red("Options --diff and --check not allowed. Please remove -D, --diff, -C, --check."))
                puts("These ansible-playbook options are managed automatically by commcare-cloud and cannot be set manually.")
                exit(2)

            if ask_vault_pass:
                cmd_parts += ('--vault-password-file=/bin/cat',)

            cmd_parts += get_common_ssh_args(public_vars)
            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print(cmd)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True, env=ansible_context.env_vars)
            if ask_vault_pass:
                p.communicate(input='{}\n'.format(ansible_context.get_ansible_vault_password()))
            else:
                p.communicate()
            return p.returncode

        def run_check():
            return ansible_playbook(args.environment, args.playbook, '--check', *unknown_args)

        def run_apply():
            return ansible_playbook(args.environment, args.playbook, *unknown_args)

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


class _AnsiblePlaybookAlias(object):
    @staticmethod
    def make_parser(parser):
        arg_skip_check(parser)
        arg_quiet(parser)
        arg_branch(parser)
        arg_stdout_callback(parser)


class UpdateConfig(_AnsiblePlaybookAlias):
    command = 'update-config'
    help = (
        "Run the ansible playbook for updating app config "
        "such as django localsettings.py and formplayer application.properties."
    )

    @staticmethod
    def run(args, unknown_args):
        args.playbook = 'deploy_localsettings.yml'
        unknown_args += ('--tags=localsettings',)
        AnsiblePlaybook.run(args, unknown_args)


class RestartElasticsearch(_AnsiblePlaybookAlias):
    command = 'restart-elasticsearch'
    help = (
        "Do a rolling restart of elasticsearch."
    )

    @staticmethod
    def run(args, unknown_args):
        args.playbook = 'es_rolling_restart.yml'
        if not ask('Have you stopped all the elastic pillows?', strict=True, quiet=args.quiet):
            exit(0)
        puts(colored.yellow(
            "This will cause downtime on the order of seconds to minutes,\n"
            "except in a few cases where an index is replicated across multiple nodes."))
        if not ask('Do a rolling restart of the ES cluster?', strict=True, quiet=args.quiet):
            exit(0)
        AnsiblePlaybook.run(args, unknown_args)


class BootstrapUsers(_AnsiblePlaybookAlias):
    command = 'bootstrap-users'
    help = (
        "Add users to a set of new machines as root. "
        "This must be done before any other user can log in."
    )

    @staticmethod
    def run(args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        public_vars = get_public_vars(args.environment)
        root_user = public_vars.get('commcare_cloud_root_user', 'root')
        unknown_args += ('--tags=users', '-u', root_user)
        if not public_vars.get('commcare_cloud_pem'):
            unknown_args += ('--ask-pass',)
        AnsiblePlaybook.run(args, unknown_args)


def arg_inventory_group(parser):
    parser.add_argument('inventory_group', help=(
        "The inventory group to run the command on. Use 'all' for all hosts."
    ))


class RunAnsibleModule(object):
    command = 'run-module'
    help = (
        'Run an arbitrary Ansible module.'
    )

    @staticmethod
    def make_parser(parser):
        arg_inventory_group(parser)
        parser.add_argument('module', help="The module to run")
        parser.add_argument('module_args', help="The arguments to pass to the module")
        RunAnsibleModule.add_non_positional_arguments(parser)

    @staticmethod
    def add_non_positional_arguments(parser):
        parser.add_argument('-u', '--user', dest='remote_user', default='ansible', help=(
            "connect as this user (default=ansible)"
        ))
        parser.add_argument('-b', '--become', action='store_true', help=(
            "run operations with become (implies vault password prompting if necessary)"
        ))
        parser.add_argument('--become-user', help=(
            "run operations as this user (default=root)"
        ))
        arg_skip_check(parser)
        arg_quiet(parser)
        arg_stdout_callback(parser)
        add_to_help_text(parser, "\n{}\n{}".format(
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

    @staticmethod
    def run(args, unknown_args):
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
            print(cmd)
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


class RunShellCommand(object):
    command = 'run-shell-command'
    help = 'Run an arbitrary command via the shell module.'

    @staticmethod
    def make_parser(parser):
        arg_inventory_group(parser)
        parser.add_argument('shell_command', help="The shell command you want to run")
        RunAnsibleModule.add_non_positional_arguments(parser)

    @staticmethod
    def run(args, unknown_args):
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
        RunAnsibleModule.run(args, unknown_args)


class Fab(object):
    command = 'fab'
    help = (
        "Run a fab command as you would with fab"
    )

    @staticmethod
    def make_parser(parser):
        parser.add_argument(dest='fab_command', help="fab command", default=None)

    @staticmethod
    def run(args, unknown_args):
        def run_fab(args, unknown_args):
            cmd_parts = (
                'fab', '-f', FABFILE,
                args.environment,
            ) + (
                (args.fab_command,) if args.fab_command else ()
            ) + tuple(unknown_args)

            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print(cmd)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
            p.communicate()
            return p.returncode

        exit_code = run_fab(args, unknown_args)
        if exit_code == 0:
            puts(colored.green(u"✓ Fab completed with status code {}".format(exit_code)))
        else:
            puts(colored.red(u"✗ Fab failed with status code {}".format(exit_code)))


class Lookup(object):
    command = 'lookup'
    help = "Lookup remote hostname or IP address"

    @classmethod
    def make_parser(cls, parser):
        cls.parser = parser
        parser.add_argument("server",
            help="Server name/group: postgresql, proxy, webworkers, ... The server "
                 "name/group may be prefixed with 'username@' to login as a specific "
                 "user and may be terminated with ':<n>' to choose one of "
                 "multiple servers if there is more than one in the group. "
                 "For example: webworkers:0 will pick the first webworker.")

    @classmethod
    def lookup_server_address(cls, args):
        def exit(message):
            cls.parser.error("\n" + message)
        return get_server_address(args.environment, args.server, exit)

    @classmethod
    def run(cls, args, unknown_args):
        if unknown_args:
            sys.stderr.write(
                "Ignoring extra argument(s): {}\n".format(unknown_args)
            )
        print(cls.lookup_server_address(args))


class Ssh(Lookup):
    command = 'ssh'
    help = "Connect to a remote host with ssh"

    @classmethod
    def run(cls, args, ssh_args):
        address = cls.lookup_server_address(args)
        cmd_parts = [cls.command, address] + ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print(cmd)
        os.execvp(cls.command, cmd_parts)


class Mosh(Ssh):
    command = 'mosh'
    help = "Connect to a remote host with mosh"


def git_branch():
    cwd = ANSIBLE_DIR
    git_branch_output = subprocess.check_output("git branch", cwd=cwd, shell=True).strip().split('\n')
    starred_line, = [line for line in git_branch_output if line.startswith('*')]
    if re.search(r'\* \(.*detached .*\)', starred_line):
        return starred_line.split(' ')[4][:-1]
    elif re.search(r'\* \w+', starred_line):
        return starred_line.split(' ')[1]
    else:
        assert False, "Unable to parse branch name or commit: {}".format(starred_line)


def check_branch(args):
    branch = git_branch()
    if args.branch != branch:
        if branch != 'master':
            puts(colored.red("You are not on branch master. To deploy anyway, use --branch={}".format(branch)))
        else:
            puts(colored.red("You are on branch master. To deploy, remove --branch={}".format(args.branch)))
        exit(-1)


STANDARD_ARGS = [
    AnsiblePlaybook,
    UpdateConfig,
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
    parser = ArgumentParser()
    available_envs = sorted(
        env for env in os.listdir(ENVIRONMENTS_DIR)
        if os.path.exists(get_public_vars_filepath(env))
        and os.path.exists(get_inventory_filepath(env))
    )
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
