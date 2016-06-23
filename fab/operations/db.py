import datetime
import time

from fabric.context_managers import cd, settings
from fabric.api import roles, sudo, env, parallel

from ..exceptions import PreindexNotFinished
from ..const import ROLES_DB_ONLY


@roles(ROLES_DB_ONLY)
def preindex_views():
    with cd(env.code_root):
        sudo((
            'echo "{virtualenv_root}/bin/python '
            '{code_root}/manage.py preindex_everything '
            '8 {user}" --mail | at -t `date -d "5 seconds" '
            '+%m%d%H%M.%S`'
        ).format(
            virtualenv_root=env.virtualenv_root,
            code_root=env.code_root,
            user=env.user,
        ))
        # staticfiles.version_static()


def ensure_preindex_completion():
    max_wait = datetime.timedelta(minutes=5)
    pause_length = datetime.timedelta(seconds=5)
    start = datetime.datetime.utcnow()

    _is_preindex_complete()

    done = False
    while not done and datetime.datetime.utcnow() - start < max_wait:
        time.sleep(pause_length.seconds)
        if _is_preindex_complete():
            done = True
        pause_length *= 2

    if not done:
        raise PreindexNotFinished()


@roles(ROLES_DB_ONLY)
def _is_preindex_complete(code_root, virtualenv_root, user):
    with settings(warn_only=True):
        return sudo(
            ('{virtualenv_root}/bin/python '
            '{code_root}/manage.py preindex_everything '
            '--check').format(
                virtualenv_root=virtualenv_root,
                code_root=code_root,
                user=user,
            ),
        ).succeeded


@roles(ROLES_DB_ONLY)
@parallel
def flip_es_aliases():
    """Flip elasticsearch aliases to the latest version"""
    with cd(env.code_root):
        sudo('%(virtualenv_root)s/bin/python manage.py ptop_es_manage --flip_all_aliases' % env)


@roles(ROLES_DB_ONLY)
def migrate():
    """run migrations on remote environment"""
    with cd(env.code_root):
        sudo('%(virtualenv_root)s/bin/python manage.py sync_finish_couchdb_hq' % env)
        sudo('%(virtualenv_root)s/bin/python manage.py migrate_multi --noinput' % env)


@roles(ROLES_DB_ONLY)
def set_in_progress_flag(use_current_release=False):
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py deploy_in_progress'.format(venv))
