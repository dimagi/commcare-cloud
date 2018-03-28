from __future__ import absolute_import

from fabric.api import roles, sudo, env
from fabric.context_managers import cd

from ..const import ROLES_AIRFLOW

@roles(ROLES_AIRFLOW)
def deploy_airflow():
    with cd(env.airflow_code_root):
        sudo('git remote prune origin')
        sudo('git pull')
        sudo("find . -name '*.pyc' -delete")
