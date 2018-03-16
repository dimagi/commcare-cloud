import getpass
import os

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import ANSIBLE_DIR
from six.moves import shlex_quote
from fabric.api import env

DEPRECATED_ANSIBLE_ARGS = [
    '--sudo',
    '--sudo-user',
    '--su',
    '--su-user',
    '--ask-sudo-pass',
    '--ask-su-pass',
]


class AnsibleContext(object):
    def __init__(self, args):
        self._ansible_vault_password = None
        self.env_vars = self._build_env(args)

    def get_ansible_vault_password(self):
        if self._ansible_vault_password is None:
            self._ansible_vault_password = getpass.getpass("Vault Password: ")
        return self._ansible_vault_password

    def _build_env(self, args):
        """Look for args that have been flagged as environment variables
        and add them to the env dict with appropriate naming
        """
        env = os.environ.copy()
        env['ANSIBLE_CONFIG'] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
        if hasattr(args, 'stdout_callback'):
            env['ANSIBLE_STDOUT_CALLBACK'] = args.stdout_callback
        return env


def get_common_ssh_args(public_vars):
    pem = public_vars.get('commcare_cloud_pem', None)
    strict_host_key_checking = public_vars.get('commcare_cloud_strict_host_key_checking', True)

    common_ssh_args = []
    if pem:
        common_ssh_args.extend(['-i', pem])
    if not strict_host_key_checking:
        common_ssh_args.append('-o StrictHostKeyChecking=no')

    cmd_parts = tuple()
    if common_ssh_args:
        cmd_parts += ('--ssh-common-args', ' '.join(shlex_quote(arg) for arg in common_ssh_args))
    return cmd_parts


def get_celery_worker_name(environment_name, comma_separated_queue_name, worker_num):
    environment = get_environment(environment_name)
    environment_environment = environment.translated_app_processes_config.environment
    project = environment.fab_settings_config.project
    return "{project}-{environment}-celery_{comma_separated_queue_name}_{worker_num}".format(
        project=project,
        environment=environment_environment,
        comma_separated_queue_name=comma_separated_queue_name,
        worker_num=worker_num
    )


def get_django_webworker_name(environment_name):
    environment = get_environment(environment_name)
    environment_environment = environment.translated_app_processes_config.environment
    project = environment.fab_settings_config.project
    return "{project}-{environment}-django".format(
        project=project,
        environment=environment_environment
    )


def get_formplayer_instance_name(environment_name):
    environment = get_environment(environment_name)
    environment_environment = environment.translated_app_processes_config.environment
    project = environment.fab_settings_config.project
    return "{project}-{environment}-formsplayer".format(
        project=project,
        environment=environment_environment
    )


def get_formplayer_spring_instance_name(environment_name):
    environment = get_environment(environment_name)
    environment_environment = environment.translated_app_processes_config.environment
    project = environment.fab_settings_config.project
    return "{project}-{environment}-formsplayer-spring".format(
        project=project,
        environment=environment_environment
    )
