from __future__ import absolute_import, print_function, unicode_literals
import os
import subprocess
from six.moves import shlex_quote

from clint.textui import puts

from commcare_cloud.cli_utils import print_command
from commcare_cloud.colors import color_notice
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import put_virtualenv_bin_on_the_path, \
    ANSIBLE_ROLES_PATH, ANSIBLE_DIR, ANSIBLE_COLLECTIONS_PATHS


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

        if not os.path.exists(ANSIBLE_COLLECTIONS_PATHS):
            os.makedirs(ANSIBLE_COLLECTIONS_PATHS)

        env['ANSIBLE_ROLES_PATH'] = ANSIBLE_ROLES_PATH
        env['ANSIBLE_COLLECTIONS_PATHS'] = ANSIBLE_COLLECTIONS_PATHS
        requirements_yml = os.path.join(ANSIBLE_DIR, 'requirements.yml')
        cmd_roles_parts = ['ansible-galaxy', 'install', '-f', '-r', requirements_yml]
        cmd_collection_parts = ['ansible-galaxy', 'collection', 'install', '-f', '-r', requirements_yml]

        for cmd_parts in (cmd_roles_parts, cmd_collection_parts):
            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print_command(cmd)
            try:
                subprocess.check_output(cmd, shell=True, env=env)
            except subprocess.CalledProcessError as err:
                print("process exited with error: %s" % err.returncode)
                return err.returncode

        puts(color_notice("To finish first-time installation, run `manage-commcare-cloud configure`"))
        return 0
