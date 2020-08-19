from __future__ import absolute_import

import os

from fabric.api import roles, parallel, sudo, env
from fabric.context_managers import cd
from fabric.contrib import files

from commcare_cloud.fab.utils import bower_command

from ..const import (
    ROLES_STATIC,
    ROLES_DJANGO,
    ROLES_ALL_SRC,
    ROLES_CELERY,
    YARN_LOCK,
    ROLES_STATIC_PRIMARY,
)


@roles(set(ROLES_STATIC + ROLES_DJANGO))
@parallel
def version_static():
    """
    Put refs on all static references to prevent stale browser cache hits when things change.
    This needs to be run on the WEB WORKER since the web worker governs the actual static
    reference.

    """
    cmd = 'resource_static'
    with cd(env.code_root):
        sudo(
            '{venv}/bin/python manage.py {cmd}'.format(
                venv=env.py3_virtualenv_root, cmd=cmd
            ),
        )


@parallel
@roles(set(ROLES_STATIC + ROLES_DJANGO))
def bower_install():
    yarn_lock = os.path.join(env.code_root, YARN_LOCK)
    if files.exists(yarn_lock, use_sudo=True):
        return

    with cd(env.code_root):
        config = {
            'interactive': 'false',
        }
        if env.http_proxy:
            config.update({
                    'proxy': "http://{}".format(env.http_proxy),
                    'https-proxy': "http://{}".format(env.http_proxy)
            })
        bower_command('prune', production=True, config=config)
        bower_command('update', production=True, config=config)


@parallel
@roles(ROLES_STATIC + ROLES_DJANGO + ROLES_CELERY)
def npm_install():
    yarn_lock = os.path.join(env.code_root, YARN_LOCK)
    if files.exists(yarn_lock, use_sudo=True):
        return

    with cd(env.code_root):
        sudo('npm prune --production')
        sudo('npm install --production')
        sudo('npm update --production')


@parallel
@roles(ROLES_STATIC + ROLES_DJANGO + ROLES_CELERY)
def yarn_install():
    yarn_lock = os.path.join(env.code_root, YARN_LOCK)
    if not files.exists(yarn_lock, use_sudo=True):
        return

    with cd(env.code_root):
        sudo('yarn install --production')


@parallel
@roles(set(ROLES_STATIC + ROLES_DJANGO))
def collectstatic(use_current_release=False):
    """
    Collect static after a code update
    Must run on web workers for same reasons as version_static.
    """
    venv = env.py3_virtualenv_root if not use_current_release else env.py3_virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py collectstatic --noinput -v 0'.format(venv))
        sudo('{}/bin/python manage.py fix_less_imports_collectstatic'.format(venv))
        sudo('{}/bin/python manage.py compilejsi18n'.format(venv))
        sudo('{}/bin/python manage.py build_requirejs'.format(venv))


@parallel
@roles(ROLES_STATIC_PRIMARY)
def compress(use_current_release=False):
    """Run Django Compressor after a code update"""
    venv = env.py3_virtualenv_root if not use_current_release else env.py3_virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py compress --force -v 0'.format(venv))
        sudo('{}/bin/python manage.py purge_compressed_files'.format(venv))

    push_manifest(use_current_release=use_current_release)


def push_manifest(use_current_release=False):
    if env.use_shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            git_hash = _get_git_hash()
            sudo('mkdir -p {env.shared_dir_for_staticfiles}/{git_hash}')
            # copy staticfiles/CACHE/** to {env.shared_dir_for_staticfiles}/{git_hash}/staticfiles/CACHE/**
            sudo("rsync -r --delete"
                 " --include='staticfiles/' --include='CACHE/' --include='staticfiles/CACHE/**' --exclude='*'"
                 " . {env.shared_dir_for_staticfiles}/{git_hash}"
                 .format(env=env, git_hash=git_hash))
    else:
        update_manifest(save=True, use_current_release=use_current_release)


@roles(ROLES_DJANGO)
@parallel
def pull_manifest(use_current_release=False):
    if env.use_shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            git_hash = _get_git_hash()
            sudo('mkdir -p staticfiles/CACHE/')
            sudo('cp {env.shared_dir_for_staticfiles}/{git_hash}/staticfiles/CACHE/manifest.json '
                 'staticfiles/CACHE/manifest.json'
                 .format(env=env, git_hash=git_hash))
    else:
        return update_manifest(save=False, soft=False, use_current_release=use_current_release)


@roles(ROLES_STATIC)
@parallel
def pull_staticfiles_cache(use_current_release=False):
    if env.use_shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            git_hash = _get_git_hash()
            sudo('mkdir -p staticfiles/CACHE/')
            sudo('rsync -r --delete {env.shared_dir_for_staticfiles}/{git_hash}/staticfiles/CACHE/ '
                 'staticfiles/CACHE/'
                 .format(env=env, git_hash=git_hash))


def _get_git_hash():
    return sudo('git rev-parse HEAD').strip()


def update_manifest(save=False, soft=False, use_current_release=False):
    """
    Puts the manifest.json file with the references to the compressed files
    from the proxy machines to the web workers. This must be done on the WEB WORKER, since it
    governs the actual static reference.

    save=True saves the manifest.json file to redis, otherwise it grabs the
    manifest.json file from redis and inserts it into the staticfiles dir.
    """
    withpath = env.code_root if not use_current_release else env.code_current
    venv = env.py3_virtualenv_root if not use_current_release else env.py3_virtualenv_current

    args = ''
    if save:
        args = ' save'
    if soft:
        args = ' soft'
    cmd = 'update_manifest%s' % args
    with cd(withpath):
        sudo('{venv}/bin/python manage.py {cmd}'.format(venv=venv, cmd=cmd))


@roles(ROLES_ALL_SRC)
@parallel
def update_translations():
    with cd(env.code_root):
        update_locale_command = '{virtualenv_root}/bin/python manage.py update_django_locales'.format(
            virtualenv_root=env.py3_virtualenv_root,
        )
        update_translations_command = '{virtualenv_root}/bin/python manage.py compilemessages -v 0'.format(
            virtualenv_root=env.py3_virtualenv_root,
        )
        sudo(update_locale_command)
        sudo(update_translations_command)
