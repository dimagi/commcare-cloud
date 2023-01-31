from __future__ import absolute_import
from __future__ import unicode_literals

from fabric.context_managers import cd
from fabric.api import roles, sudo, env

from ..const import ROLES_DEPLOY


@roles(ROLES_DEPLOY)
def migrate():
    """run migrations on remote environment"""
    with cd(env.code_root):
        sudo(f'{env.virtualenv_root}/bin/python manage.py migrate_multi --noinput')


@roles(ROLES_DEPLOY)
def set_in_progress_flag(use_current_release=False):
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo(f'{venv}/bin/python manage.py deploy_in_progress')


@roles(ROLES_DEPLOY)
def create_kafka_topics():
    """Create kafka topics if needed.  This is pretty fast."""
    with cd(env.code_root):
        sudo(f'{env.virtualenv_root}/bin/python manage.py create_kafka_topics')
