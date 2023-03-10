from __future__ import absolute_import

from __future__ import unicode_literals

from fabric.api import roles, parallel, sudo, env
from fabric.context_managers import cd

from ..const import (
    ROLES_STATIC,
    ROLES_DJANGO,
    ROLES_ALL_SRC,
)


@roles(ROLES_DJANGO)
@parallel
def pull_manifest(use_current_release=False):
    if env.shared_dir_for_staticfiles:
        with cd(env.code_root if not use_current_release else env.code_current):
            shared_path = f"{env.shared_dir_for_staticfiles}/{_get_git_hash()}"
            sudo('mkdir -p staticfiles/CACHE/')
            sudo(f'cp {shared_path}/staticfiles/CACHE/manifest.json staticfiles/CACHE/manifest.json')
    else:
        return update_manifest(save=False, soft=False, use_current_release=use_current_release)


@roles(ROLES_STATIC)
@parallel
def pull_staticfiles_cache(use_current_release=False):
    if env.shared_dir_for_staticfiles:
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
