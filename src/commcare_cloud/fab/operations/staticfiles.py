from __future__ import absolute_import

from __future__ import unicode_literals

from fabric.api import roles, parallel, sudo, env
from fabric.context_managers import cd

from ..const import ROLES_STATIC


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
