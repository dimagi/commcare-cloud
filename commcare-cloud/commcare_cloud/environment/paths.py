import os
import sys

from memoized import memoized_property

REPO_BASE = os.path.expanduser('~/.commcare-cloud/repo')
ANSIBLE_DIR = os.path.join(REPO_BASE, 'ansible')
ENVIRONMENTS_DIR = os.environ.get('COMMCARE_CLOUD_ENVIRONMENTS', os.path.join(REPO_BASE, 'environments'))
FAB_DIR = os.path.join(REPO_BASE, 'fab')
FABFILE = os.path.join(REPO_BASE, 'fabfile.py')


class DefaultPaths(object):
    def __init__(self, env_name):
        self.env_name = env_name

    @memoized_property
    def public_yml(self):
        return os.path.join(ENVIRONMENTS_DIR, self.env_name, 'public.yml')

    @memoized_property
    def vault_yml(self):
        return os.path.join(ENVIRONMENTS_DIR, self.env_name, 'vault.yml')

    @memoized_property
    def known_hosts(self):
        return os.path.join(ENVIRONMENTS_DIR, self.env_name, 'known_hosts')

    @memoized_property
    def inventory_ini(self):
        return os.path.join(ENVIRONMENTS_DIR, self.env_name, 'inventory.ini')

    @memoized_property
    def app_processes_yml(self):
        return os.path.join(REPO_BASE, 'environments', self.env_name, 'app-processes.yml')

    @memoized_property
    def app_processes_yml_default(self):
        return os.path.join(REPO_BASE, 'environmental-defaults', 'app-processes.yml')

    @memoized_property
    def fab_settings_yml(self):
        return os.path.join(ENVIRONMENTS_DIR, self.env_name, 'fab-settings.yml')

    @memoized_property
    def fab_settings_yml_default(self):
        return os.path.join(REPO_BASE, 'environmental-defaults', 'fab-settings.yml')


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
