from __future__ import absolute_import
import datetime
import os

from fabric import utils
from fabric.api import roles, env, sudo
from fabric.context_managers import cd
from fabric.contrib import console
from fabric.contrib import files

from ..const import ROLES_FORMPLAYER, FORMPLAYER_BUILD_DIR, DATE_FMT


@roles(ROLES_FORMPLAYER)
def build_formplayer(use_current_release=False):
    """
    the dir structure ends up looking like this:
    ~/www/$ENV/current/formplayer_build
        formplayer__2017-08-23_16.16/
            libs/formplayer.jar
        current -> formplayer__2017-08-23_16.16
        formplayer.jar -> current/libs/formplayer.jar

    Thus the current artifacts will always be available at
      ~/www/$ENV/current/fromplayer_build/formplayer.jar and
    """
    code_dir = env.code_root if not use_current_release else env.code_current
    build_dir = os.path.join(code_dir, FORMPLAYER_BUILD_DIR)
    if not files.exists(build_dir):
        sudo('mkdir {}'.format(build_dir))

    if env.deploy_env == 'staging':
        jenkins_formplayer_build_url = 'https://s3.amazonaws.com/dimagi-formplayer-jars/staging/latest-successful/formplayer.jar'
    else:
        jenkins_formplayer_build_url = 'https://s3.amazonaws.com/dimagi-formplayer-jars/latest-successful/formplayer.jar'

    release_name = 'formplayer__{}'.format(datetime.datetime.utcnow().strftime(DATE_FMT))
    release_name_libs = os.path.join(release_name, 'libs')
    with cd(build_dir):
        sudo('mkdir -p {}'.format(release_name_libs))
        sudo("wget -nv '{}' -O {}/formplayer.jar".format(jenkins_formplayer_build_url, release_name_libs))
        sudo('ln -sfn {} current'.format(release_name))
        sudo('ln -sf current/libs/formplayer.jar formplayer.jar')


@roles(ROLES_FORMPLAYER)
def offline_build_formplayer():
    build_dir = os.path.join(env.code_root, FORMPLAYER_BUILD_DIR)

    if not files.exists(build_dir):
        sudo('mkdir {}'.format(build_dir))
    sudo('cp {}/formplayer.jar {}'.format(
        env.offline_code_dir,
        build_dir
    ))


@roles(ROLES_FORMPLAYER)
def rollback_formplayer():
    build_dir = os.path.join(env.code_current, FORMPLAYER_BUILD_DIR)
    with cd(build_dir):
        current_build = sudo('readlink -f current').split('/')[-1]

        previous_build_paths = sudo('find . -name "{}*" -type d'.format('formplayer__')).strip()
        if not previous_build_paths:
            utils.abort('No formplayer builds to rollback to.')

        builds = sorted(_get_builds(previous_build_paths.split('\n')), reverse=True)
        builds.remove(current_build)
        if not builds:
            utils.abort('No formplayer builds to rollback to.')

        rollback_build = builds[0]
        if not console.confirm('Confirm rollback to "{}"'.format(rollback_build), default=False):
            utils.abort('Action aborted.')

        sudo('ln -sfn {build_dir}/{rollback} {build_dir}/current'.format(
            build_dir=build_dir,
            rollback=rollback_build
        ))


def _get_builds(build_paths):
    builds = []
    for path in build_paths:
        filename = os.path.basename(path)
        try:
            _, date_to_delete_string = filename.split('formplayer__')
            datetime.datetime.strptime(date_to_delete_string, DATE_FMT)
        except ValueError:
            continue
        else:
            builds.append(filename)
    return builds
