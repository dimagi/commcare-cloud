from __future__ import absolute_import
from __future__ import unicode_literals
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
        cmd_roles_parts = ['ansible-galaxy', 'install', '-f', '-r', os.path.join(ANSIBLE_DIR, 'requirements.yml')]
        cmd_collection_parts = ['ansible-galaxy', 'collection', 'install', '-f', '-r', os.path.join(ANSIBLE_DIR, 'requirements.yml')]
        
        for cmd_parts in (cmd_roles_parts, cmd_collection_parts):
            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print_command(cmd)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True, env=env)
            p.communicate()

        puts(color_notice("To finish first-time installation, run `manage-commcare-cloud configure`".format()))
        return p.returncode
