import os

from fabric.api import env, local
from fab.utils import generate_bower_command
from fab.const import (
    OFFLINE_STAGING_DIR,
    HQ_ZIP_NAME,
    BOWER_ZIP_NAME,
    NPM_ZIP_NAME,
)


def prepare_zipfiles():
    local(
        'git clone --depth 1 --recursive https://github.com/dimagi/commcare-hq.git {}/commcare-hq'
        .format(OFFLINE_STAGING_DIR)
    )

    # After we've created our HQ code zip, let's get bower and npm

    # Bower
    local('cd {}/commcare-hq && {}'.format(OFFLINE_STAGING_DIR, generate_bower_command('install', {
        'interactive': 'false',
    })))
    zip_folder(
        os.path.join(OFFLINE_STAGING_DIR, BOWER_ZIP_NAME),
        os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq', 'bower_components')
    )

    # NPM
    local('cd {}/commcare-hq && npm install --production'.format(OFFLINE_STAGING_DIR))
    zip_folder(
        os.path.join(OFFLINE_STAGING_DIR, NPM_ZIP_NAME),
        os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq', 'node_modules')
    )

    prepare_pip_wheels(os.path.join('requirements', 'requirements.txt'))
    prepare_pip_wheels(os.path.join('requirements', 'prod_requirements.txt'))


def zip_folder(destination, folder):
    local('zip -r {} {}'.format(destination, folder))


def prepare_pip_wheels(requirements_file):
    local(
        'cd {}/commcare-hq && pip wheel --wheel-dir={}/wheelhouse -r {}'
        .format(OFFLINE_STAGING_DIR, OFFLINE_STAGING_DIR, requirements_file)
    )
