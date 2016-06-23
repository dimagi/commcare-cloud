from fabric.api import roles, env, sudo

from ..const import ROLES_TOUCHFORMS


@roles(ROLES_TOUCHFORMS)
def build_formplayer():
    build_dir = '{}/{}'.format(env.code_root, 'submodules/formplayer/build/libs')
    jenkins_formplayer_build_url = 'http://jenkins.dimagi.com/job/formplayer/lastSuccessfulBuild/artifact/build/libs/formplayer.jar'

    sudo('wget {} -P {}'.format(jenkins_formplayer_build_url, build_dir))
