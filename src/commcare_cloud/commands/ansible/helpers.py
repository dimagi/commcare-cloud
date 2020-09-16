# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals
import itertools
import os
from collections import namedtuple, defaultdict
from contextlib import contextmanager

from clint.textui import puts

from commcare_cloud.cli_utils import has_arg, ask
from commcare_cloud.colors import color_error, color_success
from commcare_cloud.environment.paths import ANSIBLE_DIR, ANSIBLE_ROLES_PATH, ANSIBLE_COLLECTIONS_PATHS
from six.moves import shlex_quote
from six.moves import range

DEPRECATED_ANSIBLE_ARGS = []


class AnsibleContext(object):
    config = 'ANSIBLE_CONFIG'
    roles_path = 'ANSIBLE_ROLES_PATH'
    stdout_callback = 'ANSIBLE_STDOUT_CALLBACK'
    collections_paths= 'ANSIBLE_COLLECTIONS_PATHS'

    def __init__(self, args):
        self.env_vars = self._build_env(args)

    def _build_env(self, args):
        """Look for args that have been flagged as environment variables
        and add them to the env dict with appropriate naming
        """
        env = os.environ.copy()
        env[self.config] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
        env[self.roles_path] = ANSIBLE_ROLES_PATH
        env[self.collections_paths] = ANSIBLE_COLLECTIONS_PATHS

        if hasattr(args, 'stdout_callback'):
            env[self.stdout_callback] = args.stdout_callback
        return env

    @contextmanager
    def with_vars(self, vars):
        current_vars = self.env_vars.copy()
        self.env_vars.update(vars)
        yield
        self.env_vars = current_vars


def get_common_ssh_args(environment, use_factory_auth=False):
    common_ssh_args = []
    cmd_parts_with_common_ssh_args = ()

    if use_factory_auth:
        auth_cmd_parts, auth_ssh_args = add_factory_auth_cmd(environment)
        cmd_parts_with_common_ssh_args += auth_cmd_parts
        common_ssh_args.extend(auth_ssh_args)

    for option_name, default_option_value in get_default_ssh_options(environment):
        common_ssh_args.extend(["-o", '{}={}'.format(option_name, default_option_value)])

    if common_ssh_args:
        cmd_parts_with_common_ssh_args += ('--ssh-common-args={}'.format(' '.join(common_ssh_args)),)
    return cmd_parts_with_common_ssh_args


def get_default_ssh_options(environment):
    default_ssh_options = []

    strict_host_key_checking = environment.public_vars.get('commcare_cloud_strict_host_key_checking', True)
    if not strict_host_key_checking:
        default_ssh_options.append(('StrictHostKeyChecking', 'no'))

    known_hosts_filepath = environment.paths.known_hosts
    if os.path.exists(known_hosts_filepath):
        default_ssh_options.append(('UserKnownHostsFile', known_hosts_filepath))

    return default_ssh_options


def add_factory_auth_cmd(environment):
    auth_cmd_parts = ()
    auth_ssh_args = []
    pem = environment.public_vars.get('commcare_cloud_pem', None)
    if not pem:
        auth_cmd_parts += ('--ask-pass',)
    else:
        auth_ssh_args.extend(['-i', pem])

    return auth_cmd_parts, auth_ssh_args


def get_django_webworker_name(environment):
    return _get_process_name(environment, 'django')


def get_formplayer_spring_instance_name(environment):
    return _get_process_name(environment, 'formsplayer-spring')


def _get_process_name(environment, short_name):
    deploy_env = environment.meta_config.deploy_env
    project = environment.fab_settings_config.project
    return "{project}-{deploy_env}-{short_name}".format(
        project=project,
        deploy_env=deploy_env,
        short_name=short_name
    )


def get_user_arg(public_vars, unknown_args, use_factory_auth=False):
    cmd_parts = tuple()
    if use_factory_auth:
        default_user = public_vars.get('commcare_cloud_root_user', 'root')
    else:
        default_user = 'ansible'
    if not has_arg(unknown_args, '-u', '--user'):
        user = public_vars.get('commcare_cloud_remote_user', default_user)
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
            puts(color_success("✓ Check completed with status code {}".format(exit_code)))
            user_wants_to_apply = ask('Do you want to apply these changes?',
                                      quiet=quiet)
        else:
            puts(color_error("✗ Check failed with status code {}".format(exit_code)))
            user_wants_to_apply = ask('Do you want to try to apply these changes anyway?',
                                      quiet=quiet)

    exit_code = 0
    if user_wants_to_apply:
        exit_code = run_apply()
        if exit_code == 0:
            puts(color_success("✓ Apply completed with status code {}".format(exit_code)))
        else:
            puts(color_error("✗ Apply failed with status code {}".format(exit_code)))

    return exit_code


ProcessDescriptor = namedtuple('ProcessDescriptor', 'host, short_name, number, full_name')


def get_celery_workers(environment):
    """
    A generator that yields ``ProcessDescriptor`` tuples for celery

    The same process may be yielded more than once if a single process is managing
    multiple queues.

    :param environment:
    """
    for host, queues in environment.app_processes_config.celery_processes.items():
        if not host or host == 'None':
            continue
        for comma_separated_queue_names, config in queues.items():
            for queue in comma_separated_queue_names.split(','):
                if queue == 'flower' or queue == 'beat':
                    # there's always only one, so worker_num doesn't factor into the name
                    worker_range = [None]
                else:
                    worker_range = range(config.num_workers)
                for worker_num in worker_range:
                    process_name = get_celery_worker_name(environment, comma_separated_queue_names, worker_num)
                    yield ProcessDescriptor(host, queue, worker_num, process_name)


def get_celery_worker_name(environment, comma_separated_queue_name, worker_num):
    environment_environment = environment.meta_config.deploy_env
    project = environment.fab_settings_config.project
    if comma_separated_queue_name == 'beat':
        return "{project}-{environment}-celerybeat".format(project=project, environment=environment_environment)
    return "{project}-{environment}-celery_{comma_separated_queue_name}{worker_num_suffix}".format(
        project=project,
        environment=environment_environment,
        comma_separated_queue_name=comma_separated_queue_name,
        worker_num_suffix="_{}".format(worker_num) if worker_num is not None else ''
    )


def get_pillowtop_processes(environment):
    """
    A generator that yields ``ProcessDescriptor`` tuples for pillowtop
    :param environment:
    """
    for host, pillows in environment.app_processes_config.pillows.items():
        for name, params in pillows.items():
            start = params.start_process
            num_processes = params.num_processes
            for num_process in range(start, start + num_processes):
                process_name = "commcare-hq-{deploy_env}-pillowtop-{pillow_name}-{num_process}".format(
                    deploy_env=environment.meta_config.deploy_env,
                    pillow_name=name,
                    num_process=num_process
                )
                yield ProcessDescriptor(host, name, num_process, process_name)


def get_management_command_processes(environment):
    project = environment.fab_settings_config.project
    deploy_env = environment.meta_config.deploy_env
    for host, command_names in environment.app_processes_config.management_commands.items():
        for command_name, params in command_names.items():
            process_name = "{project}-{deploy_env}-{command_name}".format(
                project=project, deploy_env=deploy_env, command_name=command_name
            )
            yield ProcessDescriptor(host, command_name, 0, process_name)


def _get_simple_processes(environment, inventory_group, process_name):
    for host in environment.groups.get(inventory_group, []):
        yield ProcessDescriptor(host, process_name, 0, process_name)


def get_all_supervisor_processes_by_host(environment):
    by_host = defaultdict(list)

    processes = itertools.chain(
        get_pillowtop_processes(environment),
        get_celery_workers(environment),
        get_management_command_processes(environment),
        _get_simple_processes(environment, 'webworkers', get_django_webworker_name(environment)),
        _get_simple_processes(environment, 'formplayer', get_formplayer_spring_instance_name(environment)),
        _get_simple_processes(environment, 'airflow', _get_process_name(environment, 'airflow_scheduler')),
        _get_simple_processes(environment, 'airflow', _get_process_name(environment, 'airflow_webserver')),
        _get_simple_processes(environment, 'proxy', _get_process_name(environment, 'websockets')),
    )
    for process in processes:
        by_host[process.host].append(process.full_name)

    return by_host
