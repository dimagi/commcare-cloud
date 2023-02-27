from __future__ import absolute_import
from __future__ import unicode_literals

from fabric.context_managers import cd, settings, hide
from fabric.api import roles, sudo, env
from fabric.decorators import runs_once

from ..const import ROLES_PILLOWTOP, ROLES_DEPLOY


@roles(ROLES_PILLOWTOP)
@runs_once
def preindex_views():
    with cd(env.code_root):
        command = f'{env.virtualenv_root}/bin/python {env.code_root}/manage.py preindex_everything 8 {env.user}'
        mail_flag = '--mail' if env.email_enabled else ''
        sudo(f'echo "{command}" {mail_flag} | at -t `date -d "5 seconds" +%m%d%H%M.%S`')


@roles(ROLES_DEPLOY)
def ensure_checkpoints_safe():
    extras = '--print-only' if env.ignore_kafka_checkpoint_warning else ''
    with cd(env.code_root):
        try:
            sudo(f'{env.virtualenv_root}/bin/python manage.py validate_kafka_pillow_checkpoints {extras}')
        except Exception:
            if env.ignore_kafka_checkpoint_warning:
                # if we were forcing and still got an error this is likely a bug so we should raise it
                raise
            raise Exception(
                "Deploy failed, likely because kafka checkpoints weren't available.\n"
                "Scroll up for more detailed information.\n"
                "You can rerun with --set ignore_kafka_checkpoint_warning=true "
                "to prevent this error from blocking the deploy."
            )


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
