# coding=utf-8
from __future__ import print_function
import getpass
import os
from six.moves import input, shlex_quote
from argparse import ArgumentParser
import subprocess
from clint.textui import puts, colored


def ask(message):
    return 'y' == input('{} [y/N]'.format(message))


def arg_skip_check(parser):
    parser.add_argument('--skip-check', action='store_true', default=False, help=(
        "skip the default of viewing --check output first"
    ))


def arg_branch(parser):
    parser.add_argument('--branch', default='master', help=(
        "the name of the commcarehq-ansible git branch to run against, if not master"
    ))


class AnsiblePlaybook(object):
    command = 'ansible-playbook'
    help = (
        "Run a playbook as you would with ansible-playbook, "
        "but with boilerplate settings already set based on your <environment>. "
        "By default, you will see --check output and then asked whether to apply. "
        "All arguments not specified here will be passed on to ansible-playbook."
    )

    @staticmethod
    def make_parser(parser):
        arg_skip_check(parser)
        arg_branch(parser)
        parser.add_argument('playbook', help=(
            "The ansible playbook .yml file to run."
        ))

    @staticmethod
    def run(args, unknown_args):
        check_branch(args)

        def ansible_playbook(environment, playbook, vault_password, *cmd_args):
            cmd_parts = (
                'ANSIBLE_CONFIG={}'.format(os.path.expanduser('~/.commcare-cloud/ansible/ansible.cfg')),
                'ansible-playbook',
                os.path.expanduser('~/.commcare-cloud/ansible/{playbook}'.format(playbook=playbook)),
                '-u', 'ansible',
                '-i', os.path.expanduser('~/.commcare-cloud/inventory/{env}'.format(env=environment)),
                '-e', '@{}'.format(os.path.expanduser('~/.commcare-cloud/vars/{env}/{env}_vault.yml'.format(env=environment))),
                '-e', '@{}'.format(os.path.expanduser('~/.commcare-cloud/vars/{env}/{env}_public.yml'.format(env=environment))),
                '--vault-password-file=/bin/cat',
                '--diff',
            ) + cmd_args
            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print(cmd)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
            p.communicate(input='{}\n'.format(vault_password))
            return p.returncode

        def run_check():
            return ansible_playbook(args.environment, args.playbook, get_ansible_vault_password(), '--check', *unknown_args)

        def run_apply():
            return ansible_playbook(args.environment, args.playbook, get_ansible_vault_password(), *unknown_args)

        def get_ansible_vault_password():
            if get_ansible_vault_password.value is None:
                get_ansible_vault_password.value = getpass.getpass("Vault Password: ")
            return get_ansible_vault_password.value
        get_ansible_vault_password.value = None

        exit_code = 0

        if args.skip_check:
            user_wants_to_apply = ask('Do you want to apply without running the check first?')
        else:
            exit_code = run_check()
            if exit_code == 1:
                # this means there was an error before ansible was able to start running
                exit(exit_code)
                return  # for IDE
            elif exit_code == 0:
                puts(colored.green(u"✓ Check completed with status code {}".format(exit_code)))
                user_wants_to_apply = ask('Do you want to apply these changes?')
            else:
                puts(colored.red(u"✗ Check failed with status code {}".format(exit_code)))
                user_wants_to_apply = ask('Do you want to try to apply these changes anyway?')

        if user_wants_to_apply:
            exit_code = run_apply()
            if exit_code == 0:
                puts(colored.green(u"✓ Apply completed with status code {}".format(exit_code)))
            else:
                puts(colored.red(u"✗ Apply failed with status code {}".format(exit_code)))

        exit(exit_code)


class UpdateConfig(object):
    command = 'update-config'
    help = (
        "Run the ansible playbook for updating app config "
        "such as django localsettings.py and formplayer application.properties."
    )

    @staticmethod
    def make_parser(parser):
        arg_skip_check(parser)
        arg_branch(parser)

    @staticmethod
    def run(args, unknown_args):
        args.playbook = 'deploy_localsettings.yml'
        unknown_args += ('--tags=localsettings',)
        AnsiblePlaybook.run(args, unknown_args)


def git_branch():
    return subprocess.check_output("git branch | grep '^*' | cut -d' ' -f2", shell=True,
                                   cwd=os.path.expanduser('~/.commcare-cloud/ansible')).strip()


def check_branch(args):
    branch = git_branch()
    if args.branch != branch:
        if branch != 'master':
            puts(colored.red("You are not on branch master. To deploy anyway, use --branch={}".format(branch)))
        else:
            puts(colored.red("You are on branch master. To deploy, remove --branch={}".format(branch)))
        exit(-1)

STANDARD_ARGS = [
    AnsiblePlaybook,
    UpdateConfig,
]


def main():
    parser = ArgumentParser()
    inventory_dir = os.path.expanduser('~/.commcare-cloud/inventory/')
    vars_dir = os.path.expanduser('~/.commcare-cloud/vars/')
    if os.path.isdir(inventory_dir) and os.path.isdir(vars_dir):
        available_envs = sorted(set(os.listdir(inventory_dir)) & set(os.listdir(vars_dir)))
    else:
        available_envs = []
    parser.add_argument('environment', choices=available_envs, help=(
        "server environment to run against"
    ))
    subparsers = parser.add_subparsers(dest='command')

    for standard_arg in STANDARD_ARGS:
        standard_arg.make_parser(subparsers.add_parser(subparsers.command, help=standard_arg.help))

    args, unknown_args = parser.parse_known_args()
    for standard_arg in STANDARD_ARGS:
        if args.command == standard_arg.command:
            standard_arg.run(args, unknown_args)

if __name__ == '__main__':
    main()
