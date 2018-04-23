from __future__ import absolute_import

import os
import subprocess
import textwrap

from argparse import ArgumentParser

from clint.textui import puts, colored
from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command, ask
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import ANSIBLE_ROLES_PATH, ANSIBLE_DIR, \
    put_virtualenv_bin_on_the_path, PACKAGE_BASE, get_virtualenv_bin_path, DIMAGI_ENVIRONMENTS_DIR


class Install(CommandBase):
    command = 'install'
    help = "Finishes the commcare-cloud install, including installing ansible-galaxy roles"

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        env = os.environ.copy()
        put_virtualenv_bin_on_the_path()
        if not os.path.exists(ANSIBLE_ROLES_PATH):
            os.makedirs(ANSIBLE_ROLES_PATH)

        env['ANSIBLE_ROLES_PATH'] = ANSIBLE_ROLES_PATH
        cmd_parts = ['ansible-galaxy', 'install', '-r', os.path.join(ANSIBLE_DIR, 'requirements.yml')]
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True, env=env)
        p.communicate()

        puts(colored.blue("To finish first-time installation, run `manage-commcare-cloud configure`".format()))
        return p.returncode


class Configure(CommandBase):
    command = 'configure'
    help = 'Guide to setting up everything you need to work with commcare-cloud'

    def make_parser(self):
        self.parser.add_argument('--environments-dir')
        self.parser.add_argument('--quiet', action='store_true')

    @staticmethod
    def _determine_environments_dir(quiet):
        environments_dir = None

        environ_value = os.environ.get('COMMCARE_CLOUD_ENVIRONMENTS')

        if quiet:
            return environ_value or DIMAGI_ENVIRONMENTS_DIR

        def have_same_realpath(dir1, dir2):
            return os.path.realpath(dir1) == os.path.realpath(dir2)

        if not environments_dir:
            if os.path.exists(DIMAGI_ENVIRONMENTS_DIR):
                if ask("Do you work or contract for Dimagi?"):
                    print("OK, we'll give you Dimagi's default environments (production, staging, etc.).")
                    environments_dir = DIMAGI_ENVIRONMENTS_DIR

        if not environments_dir:
            if environ_value and not have_same_realpath(environ_value, DIMAGI_ENVIRONMENTS_DIR):
                print("I see you have COMMCARE_CLOUD_ENVIRONMENTS set to {} in your environment".format(environ_value))
                if ask("Would you like to use environments at that location?"):
                    environments_dir = environ_value

        if not environments_dir:
            default_environments_dir = "~/.commcare-cloud/environments"
            environments_dir = os.path.expanduser(default_environments_dir)
            print("To use commcare-cloud, you have to have an environments directory. "
                  "This is where you will store information about your cluster setup, "
                  "such as the IP addresses of the hosts in your cluster, "
                  "how different services are distributed across the machines, "
                  "and all settings specific to your CommCare instance.")
            if ask("Would you like me to create an empty one for you at "
                   "{}?".format(default_environments_dir)):
                for dir_name in ['_authorized_keys', '_users']:
                    dir_path = os.path.expanduser(os.path.join(default_environments_dir, dir_name))
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                print("Okay, I've got the env started for you, "
                      "but you're going to have to fill out the rest before you can do much. "
                      "For more information, see http://dimagi.github.io/commcare-cloud/env/ "
                      "and refer to the examples at "
                      "https://github.com/dimagi/commcare-cloud/tree/master/environments.")

        return environments_dir

    def run(self, args, unknown_args):
        puts(colored.blue("Let's get you set up to run commcare-cloud."))

        if args.environments_dir:
            environments_dir = args.environments_dir
        else:
            environments_dir = self._determine_environments_dir(quiet=args.quiet)

        commcare_cloud_dir = os.path.expanduser("~/.commcare-cloud")
        if not os.path.exists(commcare_cloud_dir):
            os.makedirs(commcare_cloud_dir)
        load_config_file = os.path.expanduser("~/.commcare-cloud/load_config.sh")
        if not os.path.exists(load_config_file) or ask("Overwrite your ~/.commcare-cloud/load_config.sh?"):
            with open(load_config_file, 'w') as f:
                f.write(textwrap.dedent("""
                    # auto-generated with `manage-commcare-cloud configure`:
                    export COMMCARE_CLOUD_ENVIRONMENTS={COMMCARE_CLOUD_ENVIRONMENTS}
                    export PATH=$PATH:{virtualenv_path}
                    source {PACKAGE_BASE}/.bash_completion
                """.format(
                    COMMCARE_CLOUD_ENVIRONMENTS=shlex_quote(environments_dir),
                    virtualenv_path=get_virtualenv_bin_path(),
                    PACKAGE_BASE=PACKAGE_BASE,
                )).strip())
        puts(colored.blue("Add the following to your ~/.bash_profile:"))
        puts(colored.cyan("source ~/.commcare-cloud/load_config.sh"))
        puts(colored.blue(
            "and then open a new shell. "
            "You should be able to run `commcare-cloud` without entering your virtualenv."))


class GetPath(CommandBase):
    command = 'get-path'
    help = "Print the value of a property of the commcare-cloud install"

    def make_parser(self):
        self.parser.add_argument('property', choices=['ANSIBLE_DIR'])

    def run(self, args, unknown_args):
        if args.property == 'ANSIBLE_DIR':
            print(ANSIBLE_DIR)


COMMAND_TYPES = [
    Install,
    GetPath,
    Configure,
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
