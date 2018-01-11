import os
import sys

REPO_BASE = os.path.expanduser('~/.commcare-cloud/repo')
ANSIBLE_DIR = os.path.join(REPO_BASE, 'ansible')
ENVIRONMENTS_DIR = os.path.join(REPO_BASE, 'environments')
FAB_DIR = os.path.join(REPO_BASE, 'fab')
FABFILE = os.path.join(REPO_BASE, 'fabfile.py')


def get_public_vars_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'public.yml')


def get_vault_vars_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'vault.yml')


def get_inventory_filepath(environment):
    return os.path.join(ENVIRONMENTS_DIR, environment, 'inventory.ini')


def get_virtualenv_path():
    return os.path.dirname(sys.executable)


def get_available_envs():
    return sorted(
        env for env in os.listdir(ENVIRONMENTS_DIR)
        if os.path.exists(get_public_vars_filepath(env))
        and os.path.exists(get_inventory_filepath(env))
    )
