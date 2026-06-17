import os
import shlex
import subprocess

import yaml
from clint.textui import puts

from commcare_cloud.cli_utils import print_command
from commcare_cloud.colors import color_notice, color_success
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
        env['ANSIBLE_ROLES_PATH'] = ANSIBLE_ROLES_PATH
        env['ANSIBLE_COLLECTIONS_PATHS'] = ANSIBLE_COLLECTIONS_PATHS
        requirements_yml = os.path.join(ANSIBLE_DIR, 'requirements.yml')

        if (
            os.path.exists(ANSIBLE_ROLES_PATH)
            and os.path.exists(ANSIBLE_COLLECTIONS_PATHS)
            and requirements_installed(requirements_yml, env)
        ):
            puts(color_success("✓ Ansible roles and collections are up to date."))
            return 0

        os.makedirs(ANSIBLE_ROLES_PATH, exist_ok=True)
        os.makedirs(ANSIBLE_COLLECTIONS_PATHS, exist_ok=True)

        # Uses --force to update roles when required versions change.
        cmd_parts = ['ansible-galaxy', 'install', '--force', '-r', requirements_yml]
        cmd = ' '.join(shlex.quote(arg) for arg in cmd_parts)
        print_command(cmd)
        try:
            subprocess.check_output(cmd, shell=True, env=env)
        except subprocess.CalledProcessError as err:
            print("process exited with error: %s" % err.returncode)
            return err.returncode

        puts(color_notice("To finish first-time installation, run `manage-commcare-cloud configure`"))
        return 0


def requirements_installed(requirements_yml, env):
    """Check if every role and collection pinned in requirements_yml is installed at its pinned version."""
    with open(requirements_yml) as f:
        requirements = yaml.safe_load(f)
    return (
        required_roles(requirements) <= installed_roles(env)
        and required_collections(requirements) <= installed_collections(env)
    )


def required_roles(requirements):
    """Set of (name, version) pairs for roles pinned in requirements.

    The name matches what ``ansible-galaxy role list`` reports: the explicit
    ``name`` if given, otherwise the ``src`` (e.g. a ``namespace.role`` from Galaxy).

    Every role must pin a version so it can be compared against what is
    installed; an unversioned entry is a configuration error.
    """
    return {
        (role.get('name') or role['src'], get_version(role))
        for role in requirements.get('roles') or []
    }


def required_collections(requirements):
    """Set of (name, version) pairs for collections pinned in requirements.

    Every collection must pin a version so it can be compared against what is
    installed; an unversioned entry is a configuration error.
    """
    return {
        (collection['name'], get_version(collection))
        for collection in requirements.get('collections') or []
    }


def get_version(requirement):
    version = requirement.get('version')
    if not version:
        raise ValueError(f"Item in requirements.yml has no version: {requirement}")
    return str(version)


def installed_roles(env):
    output = subprocess.check_output(['ansible-galaxy', 'role', 'list'], env=env).decode()
    return parse_roles(output)


def installed_collections(env):
    output = subprocess.check_output(['ansible-galaxy', 'collection', 'list'], env=env).decode()
    return parse_collections(output)


def parse_roles(output):
    """Parse ``ansible-galaxy role list`` output into a set of (name, version) pairs.

    Each role line looks like ``- name, version``; path headers start with ``#``.
    """
    installed = set()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('- '):
            name, _, version = line[2:].partition(', ')
            installed.add((name, version))
    return installed


def parse_collections(output):
    """Parse ``ansible-galaxy collection list`` output into a set of (name, version) pairs.

    The output is a ``namespace.name  version`` table, optionally repeated per
    collections path, with ``#`` path headers, a ``Collection Version`` header,
    and a dashed separator line that are all skipped.
    """
    installed = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and '.' in parts[0] and parts[0] != 'Collection':
            installed.add((parts[0], parts[1]))
    return installed
