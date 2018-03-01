import os
import sys

import functools
import yaml
from memoized import memoized

REPO_BASE = os.path.expanduser('~/.commcare-cloud/repo')
ANSIBLE_DIR = os.path.join(REPO_BASE, 'ansible')
ENVIRONMENTS_DIR = os.environ.get('COMMCARE_CLOUD_ENVIRONMENTS', os.path.join(REPO_BASE, 'environments'))
FAB_DIR = os.path.join(REPO_BASE, 'fab')
FABFILE = os.path.join(REPO_BASE, 'fabfile.py')


memoized_property = lambda fn: property(memoized(fn))


class DefaultPaths(object):
    def __init__(self, env_name):
        self.env_name = env_name

    @memoized_property
    def public_yml(self):
        return get_public_vars_filepath(self.env_name)

    @memoized_property
    def vault_yml(self):
        return get_vault_vars_filepath(self.env_name)

    @memoized_property
    def known_hosts(self):
        return get_known_hosts_filepath(self.env_name)

    @memoized_property
    def inventory_ini(self):
        return get_inventory_filepath(self.env_name)

    @memoized_property
    def app_processes_yml(self):
        return get_app_processes_filepath(self.env_name)

    @memoized_property
    def app_processes_yml_default(self):
        return get_default_app_processes_filepath()


def get_public_vars_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'public.yml')


def get_vault_vars_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'vault.yml')


def get_known_hosts_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'known_hosts')


def get_inventory_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'inventory.ini')


def get_app_processes_filepath(env_name):
    return os.path.join(REPO_BASE, 'environments', env_name, 'app-processes.yml')


def get_default_app_processes_filepath():
    return os.path.join(REPO_BASE, 'environmental-defaults', 'app-processes.yml')


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
        if os.path.exists(get_public_vars_filepath(env))
        and os.path.exists(get_inventory_filepath(env))
    )


def get_public_vars(environment):
    filename = get_public_vars_filepath(environment)
    with open(filename) as f:
        return yaml.load(f)
