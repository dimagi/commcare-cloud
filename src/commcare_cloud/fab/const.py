from __future__ import absolute_import
import os

PROJECT_ROOT = os.path.dirname(__file__)
REPO_BASE = os.path.realpath(os.path.join(PROJECT_ROOT, '..', '..'))


ROLES_ALL = ['all']
ROLES_ALL_SRC = [
    'django_monolith',
    'django_app',
    'django_celery',
    'django_pillowtop',
    'formsplayer',
    'formplayer',
    'staticfiles',
    'airflow',
    'django_manage'
]
ROLES_ALL_SERVICES = [
    'django_monolith',
    'django_app',
    'django_celery',
    'django_pillowtop',
    'formsplayer',
    'formplayer',
    'staticfiles',
    'airflow'
]
ROLES_CELERY = ['django_monolith', 'django_celery']
ROLES_PILLOWTOP = ['django_monolith', 'django_pillowtop']
ROLES_DJANGO = ['django_monolith', 'django_app']
ROLES_FORMPLAYER = ['django_monolith', 'formplayer']
ROLES_STATIC = ['django_monolith', 'staticfiles']
ROLES_POSTGRESQL = ['pg', 'pgstandby', 'django_monolith']
ROLES_ELASTICSEARCH = ['elasticsearch', 'django_monolith']
ROLES_RIAKCS = ['riakcs', 'django_monolith']
ROLES_DEPLOY = ['deploy', 'django_monolith']
ROLES_MANAGE = ['django_manage']
ROLES_CONTROL = ['control']
ROLES_AIRFLOW = ['airflow']

RELEASE_RECORD = 'RELEASES.txt'
KEEP_UNTIL_PREFIX = 'KEEP_UNTIL__'
DATE_FMT = '%Y-%m-%d_%H.%M'

RSYNC_EXCLUDE = (
    '.DS_Store',
    '.git',
    '*.pyc',
    '*.example',
    '*.db',
)

CACHED_DEPLOY_ENV_FILENAME = 'cached_deploy_env.pickle'
CACHED_DEPLOY_CHECKPOINT_FILENAME = 'cached_deploy_checkpoint.pickle'

FORMPLAYER_BUILD_DIR = 'formplayer_build'

OFFLINE_STAGING_DIR = 'offline-staging'
BOWER_ZIP_NAME = 'bower.tar.gz'
NPM_ZIP_NAME = 'npm.tar.gz'
WHEELS_ZIP_NAME = 'wheels.tar.gz'
