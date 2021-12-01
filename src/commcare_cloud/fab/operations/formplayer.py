from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import os

from fabric import utils
from fabric.api import roles, env, sudo
from fabric.context_managers import cd
from fabric.contrib import console
from fabric.contrib import files

from ..const import ROLES_FORMPLAYER, FORMPLAYER_BUILD_DIR, DATE_FMT


@roles(ROLES_FORMPLAYER)
def rollback_formplayer():
    build_dir = os.path.join(env.root, FORMPLAYER_BUILD_DIR)

    builds = _get_old_formplayer_builds(build_dir)
    if not builds:
        utils.abort('No formplayer builds to rollback to.')

    rollback_build = builds[0]
    if not console.confirm('Confirm rollback to "{}"'.format(rollback_build), default=False):
        utils.abort('Action aborted.')

    with cd(build_dir):
        sudo('ln -sfn {build_dir}/{rollback} {build_dir}/current'.format(
            build_dir=build_dir,
            rollback=rollback_build
        ))


def clean_formplayer_releases(keep=1):
    build_dir = os.path.join(env.root, FORMPLAYER_BUILD_DIR)
    if not files.exists(build_dir, use_sudo=True):
        return

    builds = _get_old_formplayer_builds(build_dir)
    if not builds:
        return

    with cd(os.path.join(build_dir, 'releases')):
        for build in builds[keep:]:
            sudo('rm -rf {}'.format(build))


def _get_builds(build_paths):
    builds = []
    for path in build_paths:
        filename = os.path.basename(path)
        try:
            date_to_delete_string = filename
            datetime.datetime.strptime(date_to_delete_string, DATE_FMT)
        except ValueError:
            continue
        else:
            builds.append(filename)
    return builds


def _get_old_formplayer_builds(build_dir):
    with cd(build_dir):
        current_build = sudo('readlink -f current').split('/')[-1]

        previous_build_paths = sudo('ls releases/').strip()
        if not previous_build_paths:
            return []

        old_builds = sorted(_get_builds(previous_build_paths.split('\n')), reverse=True)
        old_builds.remove(current_build)
        return old_builds
