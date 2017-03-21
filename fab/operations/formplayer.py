import os

from fabric.api import roles, env, sudo
from fabric.operations import put
from fabric.contrib import files

from ..const import ROLES_FORMPLAYER, FORMPLAYER_BUILD_DIR, OFFLINE_STAGING_DIR


@roles(ROLES_FORMPLAYER)
def build_formplayer(use_current_release=False):
    code_dir = env.code_root if not use_current_release else env.code_current
    build_dir = os.path.join(code_dir, FORMPLAYER_BUILD_DIR)
    if not files.exists(build_dir):
        sudo('mkdir {}'.format(build_dir))

    if env.environment == 'staging':
        jenkins_formplayer_build_url = 'https://jenkins.dimagi.com/job/formplayer-staging/lastSuccessfulBuild/artifact/build/libs/formplayer.jar'
    else:
        jenkins_formplayer_build_url = 'https://jenkins.dimagi.com/job/formplayer/lastSuccessfulBuild/artifact/build/libs/formplayer.jar'

    sudo('wget -nv {} -O {}/formplayer.jar'.format(jenkins_formplayer_build_url, build_dir))


@roles(ROLES_FORMPLAYER)
def offline_build_formplayer():
    build_dir = os.path.join(env.code_root, FORMPLAYER_BUILD_DIR)

    if not files.exists(build_dir):
        sudo('mkdir {}'.format(build_dir))
    sudo('cp {}/formplayer.jar {}'.format(
        env.offline_code_dir,
        build_dir
    ))
