ROLES_ALL_SRC = [
    'pg',
    'django_monolith',
    'django_app',
    'django_celery',
    'django_pillowtop',
    'formsplayer',
    'staticfiles'
]
ROLES_ALL_SERVICES = [
    'django_monolith',
    'django_app',
    'django_celery',
    'django_pillowtop',
    'formsplayer',
    'staticfiles'
]
ROLES_CELERY = ['django_monolith', 'django_celery']
ROLES_PILLOWTOP = ['django_monolith', 'django_pillowtop']
ROLES_DJANGO = ['django_monolith', 'django_app']
ROLES_TOUCHFORMS = ['django_monolith', 'formsplayer']
ROLES_STATIC = ['django_monolith', 'staticfiles']
ROLES_SMS_QUEUE = ['django_monolith', 'sms_queue']
ROLES_REMINDER_QUEUE = ['django_monolith', 'reminder_queue']
ROLES_PILLOW_RETRY_QUEUE = ['django_monolith', 'pillow_retry_queue']
ROLES_DB_ONLY = ['pg', 'django_monolith']

RELEASE_RECORD = 'RELEASES.txt'

RSYNC_EXCLUDE = (
    '.DS_Store',
    '.git',
    '*.pyc',
    '*.example',
    '*.db',
)
