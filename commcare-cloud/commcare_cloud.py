# coding=utf-8
from __future__ import print_function
import getpass
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

    @staticmethod
    def run(args, unknown_args):
        def anisible_playbook(environment, vault_password, *cmd_args):
            cmd = (
                'ansible-playbook',
                '-u', '~/.commcare-cloud/ansible',
                '-i', '~/.commcare-cloud/inventory/{env}'.format(env=environment),
                '-e', '"@~/.commcare-cloud/vars/{env}/{env}_vault.yml"'.format(env=environment),
                '-e', '"@~/.commcare-cloud/vars/{env}/{env}_public.yml"'.format(env=environment),
                '--ask-vault-pass',
                '--diff',
            ) + cmd_args
            print(' '.join(cmd))
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            p.communicate(input='{}\n'.format(vault_password))
            return p.returncode

        def run_check():
            return anisible_playbook(args.environment, get_ansible_vault_password(), '--check', *unknown_args)

        def run_apply():
            return anisible_playbook(args.environment, get_ansible_vault_password(), *unknown_args)

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


def main():
    parser = ArgumentParser()
    parser.add_argument('environment')
    subparsers = parser.add_subparsers(dest='command')

    AnsiblePlaybook.make_parser(subparsers.add_parser('ansible-playbook'))

    args, unknown_args = parser.parse_known_args()
    print(args, unknown_args)
    if args.command == 'ansible-playbook':
        AnsiblePlaybook.run(args, unknown_args)

if __name__ == '__main__':
    main()
