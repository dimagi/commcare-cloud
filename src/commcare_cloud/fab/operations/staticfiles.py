from __future__ import absolute_import

from __future__ import unicode_literals

from fabric.api import roles, parallel, sudo, env
from fabric.context_managers import cd

from ..const import (
    ROLES_STATIC,
    ROLES_DJANGO,
    ROLES_ALL_SRC,
    ROLES_CELERY,
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
    with cd(env.code_root):
        sudo(f'{env.virtualenv_root}/bin/python manage.py resource_static')


@parallel
@roles(ROLES_STATIC + ROLES_DJANGO + ROLES_CELERY)
def yarn_install():
    with cd(env.code_root):
        sudo('yarn install --production')


@parallel
@roles(set(ROLES_STATIC + ROLES_DJANGO))
def collectstatic(use_current_release=False):
    """
    Collect static after a code update
    Must run on web workers for same reasons as version_static.
    """
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        if not use_current_release:
            sudo('rm -rf staticfiles')
        sudo(f'{venv}/bin/python manage.py collectstatic --noinput -v 0')
        sudo(f'{venv}/bin/python manage.py fix_less_imports_collectstatic')
        sudo(f'{venv}/bin/python manage.py compilejsi18n')
        sudo(f'{venv}/bin/python manage.py build_requirejs')


@parallel
@roles(ROLES_STATIC_PRIMARY)
def compress(use_current_release=False):
    """Run Django Compressor after a code update"""
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo(f'{venv}/bin/python manage.py compress --force -v 0')
        sudo(f'{venv}/bin/python manage.py purge_compressed_files')

    push_manifest(use_current_release=use_current_release)


def push_manifest(use_current_release=False):
    if env.use_shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            shared_path = f"{env.shared_dir_for_staticfiles}/{_get_git_hash()}"
            sudo(f'mkdir -p {shared_path}')
            # copy staticfiles/CACHE/** to {shared_path}/staticfiles/CACHE/**
            sudo("rsync -r --delete"
                 " --include='staticfiles/' --include='CACHE/' --include='staticfiles/CACHE/**' --exclude='*'"
                 f" . {shared_path}")
    else:
        update_manifest(save=True, use_current_release=use_current_release)


@roles(ROLES_DJANGO)
@parallel
def pull_manifest(use_current_release=False):
    if env.use_shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            shared_path = f"{env.shared_dir_for_staticfiles}/{_get_git_hash()}"
            sudo('mkdir -p staticfiles/CACHE/')
            sudo(f'cp {shared_path}/staticfiles/CACHE/manifest.json staticfiles/CACHE/manifest.json')
    else:
        return update_manifest(save=False, soft=False, use_current_release=use_current_release)


@roles(ROLES_STATIC)
@parallel
def pull_staticfiles_cache(use_current_release=False):
    if env.use_shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            shared_path = f"{env.shared_dir_for_staticfiles}/{_get_git_hash()}"
            sudo('mkdir -p staticfiles/CACHE/')
            sudo(f'rsync -r --delete {shared_path}/staticfiles/CACHE/ staticfiles/CACHE/')


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
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current

    args = ''
    if save:
        args = ' save'
    if soft:
        args = ' soft'
    with cd(withpath):
        sudo(f'{venv}/bin/python manage.py update_manifest{args}')


@roles(ROLES_ALL_SRC)
@parallel
def update_translations():
    with cd(env.code_root):
        sudo(f'{env.virtualenv_root}/bin/python manage.py update_django_locales')
        sudo(f'{env.virtualenv_root}/bin/python manage.py compilemessages -v 0')
