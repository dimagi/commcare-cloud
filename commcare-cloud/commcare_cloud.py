# coding=utf-8
from __future__ import print_function
import getpass
import os
from six.moves import input
from argparse import ArgumentParser
import subprocess
from clint.textui import puts, colored


def ask(message):
    return 'y' == input('{} [y/N]'.format(message))


class AnsiblePlaybook(object):
    @staticmethod
    def make_parser(parser):
        parser.add_argument('--skip-check', action='store_true', default=False)
        parser.add_argument('--branch', default='master')
        parser.add_argument('playbook')

    @staticmethod
    def run(args, unknown_args):
        check_branch(args)

        def anisible_playbook(environment, playbook, vault_password, *cmd_args):
            cmd = (
                'ANSIBLE_CONFIG={}'.format(os.path.expanduser('~/.commcare-cloud/ansible/ansible.cfg')),
                'ansible-playbook',
                os.path.expanduser('~/.commcare-cloud/ansible/{playbook}'.format(playbook=playbook)),
                '-u', 'ansible',
                '-i', os.path.expanduser('~/.commcare-cloud/inventory/{env}'.format(env=environment)),
                '-e', '"@{}"'.format(os.path.expanduser('~/.commcare-cloud/vars/{env}/{env}_vault.yml'.format(env=environment))),
                '-e', '"@{}'.format(os.path.expanduser('~/.commcare-cloud/vars/{env}/{env}_public.yml"'.format(env=environment))),
                '--vault-password-file=/bin/cat',
                '--diff',
            ) + cmd_args
            print(' '.join(cmd))
            p = subprocess.Popen(' '.join(cmd), stdin=subprocess.PIPE, shell=True)
            p.communicate(input='{}\n'.format(vault_password))
            return p.returncode

        def run_check():
            return anisible_playbook(args.environment, args.playbook, get_ansible_vault_password(), '--check', *unknown_args)

        def run_apply():
            return anisible_playbook(args.environment, args.playbook, get_ansible_vault_password(), *unknown_args)

        def get_ansible_vault_password():
            if not get_ansible_vault_password.value:
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
    @staticmethod
    def make_parser(parser):
        parser.add_argument('--skip-check', action='store_true', default=False)
        parser.add_argument('--branch', default='master')

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


def main():
    parser = ArgumentParser()
    parser.add_argument('environment')
    subparsers = parser.add_subparsers(dest='command')

    AnsiblePlaybook.make_parser(subparsers.add_parser('ansible-playbook'))
    UpdateConfig.make_parser(subparsers.add_parser('update-config'))

    args, unknown_args = parser.parse_known_args()
    if args.command == 'ansible-playbook':
        AnsiblePlaybook.run(args, unknown_args)
    if args.command == 'update-config':
        UpdateConfig.run(args, unknown_args)

if __name__ == '__main__':
    main()
