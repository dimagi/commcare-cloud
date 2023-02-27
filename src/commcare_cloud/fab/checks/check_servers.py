from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from fabric.api import roles, env, sudo
from fabric.context_managers import cd
from fabric.decorators import runs_once

from ..const import ROLES_DEPLOY


@roles(ROLES_DEPLOY)
@runs_once
def perform_system_checks():
    path = env.code_root
    venv = env.virtualenv_root
    with cd(path):
        sudo('%s/bin/python manage.py check --deploy' % venv)
        sudo('%s/bin/python manage.py check --deploy -t database' % venv)
