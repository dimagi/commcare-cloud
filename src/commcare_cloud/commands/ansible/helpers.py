# coding=utf-8
import os

from clint.textui import puts, colored

from commcare_cloud.cli_utils import has_arg, ask
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import ANSIBLE_DIR, ANSIBLE_ROLES_PATH
from six.moves import shlex_quote

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
        self.env_vars = self._build_env(args)

    def _build_env(self, args):
        """Look for args that have been flagged as environment variables
        and add them to the env dict with appropriate naming
        """
        env = os.environ.copy()
        env['ANSIBLE_CONFIG'] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
        env['ANSIBLE_ROLES_PATH'] = ANSIBLE_ROLES_PATH
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


def get_django_webworker_name(environment_name):
    environment = get_environment(environment_name)
    environment_environment = environment.meta_config.deploy_env
    project = environment.fab_settings_config.project
    return "{project}-{environment}-django".format(
        project=project,
        environment=environment_environment
    )


def get_formplayer_instance_name(environment_name):
    environment = get_environment(environment_name)
    environment_environment = environment.meta_config.deploy_env
    project = environment.fab_settings_config.project
    return "{project}-{environment}-formsplayer".format(
        project=project,
        environment=environment_environment
    )


def get_formplayer_spring_instance_name(environment_name):
    environment = get_environment(environment_name)
    environment_environment = environment.meta_config.deploy_env
    project = environment.fab_settings_config.project
    return "{project}-{environment}-formsplayer-spring".format(
        project=project,
        environment=environment_environment
    )


def get_user_arg(public_vars, unknown_args):
    cmd_parts = tuple()
    if not has_arg(unknown_args, '-u', '--user'):
        user = public_vars.get('commcare_cloud_remote_user', 'ansible')
        cmd_parts += ('-u', user)
    return cmd_parts


def run_action_with_check_mode(run_check, run_apply, skip_check, quiet=False, always_skip_check=False):
    if always_skip_check:
        user_wants_to_apply = ask(
            'This command will apply without running the check first. Continue?',
            quiet=quiet)
    elif skip_check:
        user_wants_to_apply = ask('Do you want to apply without running the check first?',
                                  quiet=quiet)
    else:
        exit_code = run_check()
        if exit_code == 1:
            # this means there was an error before ansible was able to start running
            return exit_code
        elif exit_code == 0:
            puts(colored.green(u"✓ Check completed with status code {}".format(exit_code)))
            user_wants_to_apply = ask('Do you want to apply these changes?',
                                      quiet=quiet)
        else:
            puts(colored.red(u"✗ Check failed with status code {}".format(exit_code)))
            user_wants_to_apply = ask('Do you want to try to apply these changes anyway?',
                                      quiet=quiet)

    if user_wants_to_apply:
        exit_code = run_apply()
        if exit_code == 0:
            puts(colored.green(u"✓ Apply completed with status code {}".format(exit_code)))
        else:
            puts(colored.red(u"✗ Apply failed with status code {}".format(exit_code)))

    return exit_code
