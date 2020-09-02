from __future__ import absolute_import

import os

from fabric.api import roles, sudo, env
from fabric.context_managers import cd, shell_env

from ..const import ROLES_AIRFLOW


@roles(ROLES_AIRFLOW)
def update_airflow():
    deploy_key = env.ccc_environment.meta_config.deploy_keys.deploy_key.vault
    git_env = {"GIT_SSH_COMMAND": "ssh -i {} -o IdentitiesOnly=yes".format(
        os.path.join(env.home, ".ssh", deploy_key)
    )}
    with cd(env.airflow_code_root), shell_env(**git_env):
        sudo('git remote prune origin')
        sudo('git pull')
        sudo("find . -name '*.pyc' -delete")
