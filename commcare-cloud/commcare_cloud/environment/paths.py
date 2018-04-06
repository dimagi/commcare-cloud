import os
import sys

import yaml
from memoized import memoized_property, memoized

REPO_BASE = os.path.expanduser('~/.commcare-cloud/repo')
ANSIBLE_DIR = os.path.join(REPO_BASE, 'ansible')
ENVIRONMENTS_DIR = os.environ.get('COMMCARE_CLOUD_ENVIRONMENTS', os.path.join(REPO_BASE, 'environments'))
FAB_DIR = os.path.join(REPO_BASE, 'fab')
FABFILE = os.path.join(REPO_BASE, 'fabfile.py')


lazy_immutable_property = memoized_property


class DefaultPaths(object):
    def __init__(self, env_name, environments_dir=ENVIRONMENTS_DIR):
        self.env_name = env_name
        self.environments_dir = environments_dir

    @lazy_immutable_property
    def public_yml(self):
        return os.path.join(self.environments_dir, self.env_name, 'public.yml')

    @lazy_immutable_property
    def vault_yml(self):
        return os.path.join(self.environments_dir, self.env_name, 'vault.yml')

    @lazy_immutable_property
    def known_hosts(self):
        return os.path.join(self.environments_dir, self.env_name, 'known_hosts')

    @lazy_immutable_property
    def inventory_ini(self):
        return os.path.join(self.environments_dir, self.env_name, 'inventory.ini')

    @lazy_immutable_property
    def meta_yml(self):
        return os.path.join(self.environments_dir, self.env_name, 'meta.yml')

    @lazy_immutable_property
    def postgresql_yml(self):
        return os.path.join(self.environments_dir, self.env_name, 'postgresql.yml')

    @lazy_immutable_property
    def app_processes_yml(self):
        return os.path.join(self.environments_dir, self.env_name, 'app-processes.yml')

    @lazy_immutable_property
    def app_processes_yml_default(self):
        return os.path.join(REPO_BASE, 'environmental-defaults', 'app-processes.yml')

    @lazy_immutable_property
    def fab_settings_yml(self):
        return os.path.join(self.environments_dir, self.env_name, 'fab-settings.yml')

    @lazy_immutable_property
    def fab_settings_yml_default(self):
        return os.path.join(REPO_BASE, 'environmental-defaults', 'fab-settings.yml')

    @lazy_immutable_property
    def generated_yml(self):
        return os.path.join(self.environments_dir, self.env_name, '.generated.yml')

    @lazy_immutable_property
    def authorized_keys_dir(self):
        return os.path.join(self.environments_dir, '_authorized_keys')

    @memoized
    def get_users_yml(self, org):
        return os.path.join(self.environments_dir, '_users', '{}.yml'.format(org))


def get_role_defaults_yml(role):
    return os.path.join(REPO_BASE, 'ansible', 'roles', role, 'defaults', 'main.yml')


@memoized
def get_role_defaults(role):
    """contents of a role's defaults/main.yml, as a dict"""
    with open(get_role_defaults_yml(role)) as f:
        return yaml.load(f)


def get_virtualenv_path():
    return os.path.dirname(sys.executable)


def get_virtualenv_site_packages_path():
    for filepath in sys.path:
        if filepath.startswith(os.path.dirname(get_virtualenv_path())) and filepath.endswith('site-packages'):
            return filepath


def get_available_envs():
    if not os.path.exists(ENVIRONMENTS_DIR):
        print("The directory {!r} does not exist.\n"
              "Set COMMCARE_CLOUD_ENVIRONMENTS to a directory that exists."
              .format(ENVIRONMENTS_DIR))
        exit(1)
    return sorted(
        env for env in os.listdir(ENVIRONMENTS_DIR)
        if os.path.exists(DefaultPaths(env).public_yml)
        and os.path.exists(DefaultPaths(env).inventory_ini)
    )
