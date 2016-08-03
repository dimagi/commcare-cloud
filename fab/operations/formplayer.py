import os

from fabric.api import roles, env, sudo
from fabric.contrib import files

from ..const import ROLES_TOUCHFORMS, FORMPLAYER_BUILD_DIR


@roles(ROLES_TOUCHFORMS)
def build_formplayer():
    build_dir = os.path.join(env.code_root, FORMPLAYER_BUILD_DIR)
    if not files.exists(build_dir):
        sudo('mkdir {}'.format(build_dir))

    jenkins_formplayer_build_url = 'https://jenkins.dimagi.com/job/formplayer/lastSuccessfulBuild/artifact/build/libs/formplayer.jar'

    sudo('wget -nv {} -P {}'.format(jenkins_formplayer_build_url, build_dir))
