import os
import sys
from distutils.sysconfig import get_python_lib

import yaml
from memoized import memoized_property, memoized

from commcare_cloud.environment.exceptions import EnvironmentException


def get_virtualenv_bin_path():
    """
    Get the bin directory that the current executable is running from

    This is meant to work even when the user isn't inside a virtualenv,
    but is directly running an executable that lives in the virtualenv bin,
    so `os.environ["VIRTUAL_ENV"]` does not work here.

    """
    return os.path.dirname(sys.executable)


PACKAGE_BASE = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
ANSIBLE_ROLES_PATH = os.path.realpath(os.path.join(get_python_lib(), '.ansible/roles'))
ANSIBLE_DIR = os.path.join(PACKAGE_BASE, 'ansible')
TERRAFORM_DIR = os.path.join(PACKAGE_BASE, 'terraform')
# only works with egg install (`pip install -e .`)
DIMAGI_ENVIRONMENTS_DIR = os.path.realpath(os.path.join(PACKAGE_BASE, '..', '..', 'environments'))
ENVIRONMENTS_DIR = os.environ.get('COMMCARE_CLOUD_ENVIRONMENTS', DIMAGI_ENVIRONMENTS_DIR)
FABFILE = os.path.join(PACKAGE_BASE, 'fabfile.py')


lazy_immutable_property = memoized_property


class DefaultPaths(object):
    def __init__(self, env_name, environments_dir=None):
        self.env_name = env_name
        self.environments_dir = environments_dir or ENVIRONMENTS_DIR

    def get_env_file_path(self, filename):
        return os.path.join(self.environments_dir, self.env_name, filename)

    @lazy_immutable_property
    def public_yml(self):
        return self.get_env_file_path('public.yml')

    @lazy_immutable_property
    def vault_yml(self):
        return self.get_env_file_path('vault.yml')

    @lazy_immutable_property
    def known_hosts(self):
        return self.get_env_file_path('known_hosts')

    @lazy_immutable_property
    def inventory_ini(self):
        return self.get_env_file_path('inventory.ini')

    @lazy_immutable_property
    def inventory_ini_j2(self):
        return self.get_env_file_path('inventory.ini.j2')

    @lazy_immutable_property
    def openvpn_ini(self):
        return self.get_env_file_path('openvpn.ini')

    @lazy_immutable_property
    def inventory_csv(self):
        return self.get_env_file_path('inventory.csv')

    @lazy_immutable_property
    def inventory_directory(self):
        return self.get_env_file_path('inventory')

    @lazy_immutable_property
    def inventory_source(self):
        sources = []
        for path in [self.inventory_ini, self.inventory_csv]:
            if os.path.exists(path) and os.access(path, os.R_OK):
                sources.append(path)
        if os.path.exists(self.inventory_directory) and os.path.isdir(self.inventory_directory):
            sources.append(self.inventory_directory)

        if not sources or len(sources) > 1:
            raise EnvironmentException(
                "Exactly one inventory source must be provided. Either a single 'inventory.ini' file "
                "or a single 'inventory.csv' file or an 'inventory' folder containing inventory files."
            )
        return sources[0]

    @lazy_immutable_property
    def meta_yml(self):
        return self.get_env_file_path('meta.yml')

    @lazy_immutable_property
    def postgresql_yml(self):
        return self.get_env_file_path('postgresql.yml')

    @lazy_immutable_property
    def proxy_yml(self):
        return self.get_env_file_path('proxy.yml')

    @lazy_immutable_property
    def app_processes_yml(self):
        return self.get_env_file_path('app-processes.yml')

    @lazy_immutable_property
    def app_processes_yml_default(self):
        return os.path.join(PACKAGE_BASE, 'environmental-defaults', 'app-processes.yml')

    @lazy_immutable_property
    def fab_settings_yml(self):
        return self.get_env_file_path('fab-settings.yml')

    @lazy_immutable_property
    def fab_settings_yml_default(self):
        return os.path.join(PACKAGE_BASE, 'environmental-defaults', 'fab-settings.yml')

    @lazy_immutable_property
    def dimagi_key_store_vault(self):
        return self.get_env_file_path('DimagiKeyStore.vault')

    @lazy_immutable_property
    def generated_yml(self):
        return self.get_env_file_path('.generated.yml')

    @lazy_immutable_property
    def downtime_yml(self):
        return self.get_env_file_path('.downtime.yml')

    @lazy_immutable_property
    def terraform_yml(self):
        return self.get_env_file_path('terraform.yml')

    @lazy_immutable_property
    def authorized_keys_dir(self):
        return os.path.join(self.environments_dir, '_authorized_keys')

    def get_authorized_key_file(self, user):
        return os.path.join(self.authorized_keys_dir, '{}.pub'.format(user))

    @memoized
    def get_users_yml(self, org):
        return os.path.join(self.environments_dir, '_users', '{}.yml'.format(org))


def get_role_defaults_yml(role):
    return os.path.join(PACKAGE_BASE, 'ansible', 'roles', role, 'defaults', 'main.yml')


@memoized
def get_role_defaults(role):
    """contents of a role's defaults/main.yml, as a dict"""
    with open(get_role_defaults_yml(role)) as f:
        return yaml.load(f)


def get_available_envs(exclude_symlinks=False):
    if not os.path.exists(ENVIRONMENTS_DIR):
        print("The directory {!r} does not exist.\n"
              "Set COMMCARE_CLOUD_ENVIRONMENTS to a directory that exists."
              .format(ENVIRONMENTS_DIR))
        exit(1)
    return sorted(
        env for env in os.listdir(ENVIRONMENTS_DIR)
        if os.path.exists(DefaultPaths(env).public_yml)
        and (
            os.path.exists(DefaultPaths(env).inventory_ini)
            or os.path.exists(DefaultPaths(env).inventory_csv)
            or os.path.exists(DefaultPaths(env).inventory_directory)
        )
        and not (exclude_symlinks and os.path.islink(os.path.join(ENVIRONMENTS_DIR, env)))
    )


def put_virtualenv_bin_on_the_path():
    os.environ['PATH'] = '{}:{}'.format(get_virtualenv_bin_path(), os.environ['PATH'])
