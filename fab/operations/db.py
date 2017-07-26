import datetime
import time

from fabric.context_managers import cd, settings
from fabric.api import roles, sudo, env, parallel
from fabric.decorators import runs_once

from ..exceptions import PreindexNotFinished
from ..const import ROLES_DB_ONLY, ROLES_PILLOWTOP, ROLES_DEPLOY


@roles(ROLES_PILLOWTOP)
@runs_once
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


@roles(ROLES_DEPLOY)
def ensure_checkpoints_safe():
    extras = '--print-only' if env.force else ''
    with cd(env.code_root):
        try:
            sudo('{env.virtualenv_root}/bin/python manage.py validate_kafka_pillow_checkpoints {extras}'.format(
                env=env, extras=extras
            ))
        except Exception as e:
            if not env.force:
                message = (
                    "Deploy failed, likely because kafka checkpoints weren't available.\n"
                    "Scroll up for more detailed information.\n"
                    "You can rerun with --set force=true to prevent this error from blocking the deploy."
                ).format(e)
                raise Exception(message)
            else:
                # if we were forcing and still got an error this is likely a bug so we should raise it
                raise


@roles(ROLES_DEPLOY)
def _is_preindex_complete():
    with settings(warn_only=True):
        return sudo(
            ('{virtualenv_root}/bin/python '
            '{code_root}/manage.py preindex_everything '
            '--check').format(
                virtualenv_root=env.virtualenv_root,
                code_root=env.code_root,
                user=env.user,
            ),
        ).succeeded


@roles(ROLES_DEPLOY)
def flip_es_aliases():
    """Flip elasticsearch aliases to the latest version"""
    with cd(env.code_root):
        sudo('%(virtualenv_root)s/bin/python manage.py ptop_es_manage --flip_all_aliases' % env)


@roles(ROLES_DEPLOY)
def migrate():
    """run migrations on remote environment"""
    with cd(env.code_root):
        sudo('%(virtualenv_root)s/bin/python manage.py sync_finish_couchdb_hq' % env)
        sudo('%(virtualenv_root)s/bin/python manage.py migrate_multi --noinput' % env)


@roles(ROLES_DEPLOY)
def set_in_progress_flag(use_current_release=False):
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py deploy_in_progress'.format(venv))


@roles(ROLES_DEPLOY)
def migrations_exist():
    """
    Check if there exists database migrations to run
    """
    with cd(env.code_root):
        result = sudo('%(virtualenv_root)s/bin/python manage.py showmigrations | grep "\[ ]" | wc -l' % env)
        try:
            # This command usually returns some logging and then then number of migrations
            result = result.splitlines()
            n_migrations = int(result[-1])
        except Exception:
            # If we fail on this, return True to be safe. It's most likely cause we lost connection and
            # failed to return a value python could parse into an int
            return True
        return n_migrations > 0


@roles(ROLES_DEPLOY)
def create_kafka_topics():
    """Create kafka topics if needed.  This is pretty fast."""
    with cd(env.code_root):
        sudo('%(virtualenv_root)s/bin/python manage.py create_kafka_topics' % env)

