from __future__ import absolute_import
from __future__ import print_function
import json
import os
import time
import posixpath
from contextlib import contextmanager
import uuid

from commcare_cloud.commands.ansible.helpers import get_celery_worker_name
from fabric.api import roles, parallel, env, sudo, serial, execute
from fabric.colors import magenta
from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.operations import put, run

from ..const import (
    ROLES_CELERY,
    ROLES_DJANGO,
    ROLES_TOUCHFORMS,
    ROLES_FORMPLAYER,
    ROLES_PILLOWTOP,
    ROLES_STATIC,
    ROLES_ALL_SERVICES,
)
from fabric import utils
from six.moves import range


@task
@roles(ROLES_ALL_SERVICES)
@parallel
def set_supervisor_config():
    """Upload and link Supervisor configuration from the template."""
    set_celery_supervisorconf()


def _get_celery_queues():
    queues = {}
    queues.update(env.celery_processes.get(env.get('host_string').split(':')[0], {}))

    return queues


def _check_in_roles(roles):
    return any(env.get('host_string') in env.roledefs[role] for role in roles)


def set_celery_supervisorconf():
    if not _check_in_roles(ROLES_CELERY):
        return

    queues = _get_celery_queues()

    if 'celery_periodic' in queues and env.host != queues['celery_periodic'].get('server_whitelist'):
        show_periodic_server_whitelist_message_and_abort(env)

    _rebuild_supervisor_conf_file('make_supervisor_conf', 'celery_bash_runner.sh')
    _rebuild_supervisor_conf_file(
        'make_supervisor_conf', 'celery_bash_runner.sh',
        params={'python_options': '-O'}, conf_destination_filename='celery_bash_runner_optimized.sh'
    )

    for comma_separated_queue_names, params in queues.items():
        queue_names = comma_separated_queue_names.split(',')
        if queue_names == ['flower']:
            _rebuild_supervisor_conf_file(
                'make_supervisor_conf',
                'supervisor_celery_flower.conf',
                {'celery_params': params}
            )
            continue

        pooling = params['pooling']
        max_tasks_per_child = params['max_tasks_per_child']
        num_workers = params.get('num_workers', 1)

        params.update({
            'comma_separated_queue_names': comma_separated_queue_names,
            'pooling': pooling,
            'max_tasks_per_child': max_tasks_per_child,
        })

        for worker_num in range(num_workers):
            params.update({
                'worker_num': worker_num,
            })

            conf_destination_filename = 'supervisor_celery_worker_{}_{}.conf'.format(
                comma_separated_queue_names, worker_num)

            worker_name = get_celery_worker_name(env.ccc_environment,
                                                 params['comma_separated_queue_names'],
                                                 params['worker_num'])
            _rebuild_supervisor_conf_file(
                'make_supervisor_conf',
                'supervisor_celery_worker.conf',
                {'celery_params': params,
                 'worker_name': worker_name,
                 },
                conf_destination_filename,
            )

        if 'celery_periodic' in queue_names:
            _rebuild_supervisor_conf_file(
                'make_supervisor_conf',
                'supervisor_celery_beat.conf',
                {'celery_params': params}
            )


def show_periodic_server_whitelist_message_and_abort(env):
    utils.abort(
        "\n\n"
        "You're seeing this message as part of an effort to reduce the chance of\n"
        "deploying celery beat, which sends SMSes, fires off reminders,\n"
        "and triggers forwarders, among other things, unintentionally.\n\n"
        "For example, during a migration, you initially want to deploy everything\n"
        "except for celery beat, because you don't want both the old and new servers\n"
        "running celery beat; that screws up queuing, etc.\n\n"
        "If you...\n\n"
        '1. are really glad we caught this for you, just remove (or comment out)\n'
        '   celery_processes.{hostname}.celery_periodic\n'
        '   from environments/{env_name}/app-processes.yml\n'
        "2. know what you're doing and want to deploy celery beat to {env_name}\n"
        "   set celery_processes.{hostname}.celery_periodic.server_whitelist\n"
        '   to {host}\n'
        '   in environments/{env_name}/app-processes.yml\n'
        "3. are really confused, find someone who might know more about this\n"
        "   and ask them."
        .format(hostname=env.get('host_string').split('.')[0],
                host=env.host,
                env_name=env.env_name)
    )


def please_put(local_dir, remote_dir, temp_dir='/tmp'):
    remote_temp_dir = os.path.join(temp_dir, 'please-put-{}'.format(uuid.uuid4().hex))

    sudo('rm -rf {}'.format(remote_dir))
    sudo('mkdir -p {}'.format(os.path.dirname(remote_dir)))

    run('rm -rf {}'.format(remote_temp_dir))
    run('mkdir -p {}'.format(remote_temp_dir))

    put(local_dir, remote_temp_dir)

    sudo('cp -r {} {}'.format(os.path.join(remote_temp_dir, os.path.basename(local_dir)), remote_dir))

    run('rm -rf {}'.format(remote_temp_dir))


def _rebuild_supervisor_conf_file(conf_command, filename, params=None, conf_destination_filename=None):
    remote_service_template_dir = os.path.join(env.code_root, 'deployment', 'commcare-hq-deploy', 'fab', 'services', 'templates')
    local_service_template_dir = os.path.join(os.path.dirname(__file__), '..', 'services', 'templates')

    # put the commcare-cloud/fab/fab/services/templates directory
    # in the legacy commcare-hq-deploy location
    # so that the make_supervisor*_conf management commands know where to find it
    please_put(local_service_template_dir, remote_service_template_dir)

    sudo('mkdir -p {}'.format(posixpath.join(env.services, 'supervisor')))

    if filename in env.get('service_blacklist', []):
        print(magenta('Skipping {} because the service has been blacklisted'.format(filename)))
        return

    with cd(env.code_root):
        command = (
            '%(virtualenv_root)s/bin/python manage.py '
            '%(conf_command)s --traceback --conf_file "%(filename)s" '
            '--conf_destination "%(destination)s" --params \'%(params)s\''
        ) % {

            'conf_command': conf_command,
            'virtualenv_root': env.virtualenv_root,
            'filename': filename,
            'destination': posixpath.join(env.services, 'supervisor'),
            'params': _format_env(env, params)
        }

        if conf_destination_filename:
            command += ' --conf_destination_filename "%s"' % conf_destination_filename

        sudo(command)


def _format_env(current_env, extra=None):
    """
    formats the current env to be a foo=bar,sna=fu type paring
    this is used for the make_supervisor_conf management command
    to pass current environment to make the supervisor conf files remotely
    instead of having to upload them from the fabfile.

    This is somewhat hacky in that we're going to
    cherry pick the env vars we want and make a custom dict to return
    """
    ret = dict()
    important_props = [
        'root',
        'code_root',
        'code_current',
        'log_dir',
        'sudo_user',
        'project',
        'es_endpoint',
        'jython_home',
        'virtualenv_root',
        'virtualenv_current',
        'django_port',
        'django_bind',
        'gunicorn_workers_factor',
        'gunicorn_workers_static_factor',
        'flower_port',
        'jython_memory',
        'formplayer_memory',
        'newrelic_javaagent',
    ]

    all_hosts = env.ccc_environment.sshable_hostnames_by_group['all']

    ret['supervisor_env_vars'] = {}
    ret['command_prefix'] = ''

    if env.newrelic_djangoagent:
        host = current_env.get('host_string')
        webworkers = env.ccc_environment.groups['webworkers']
        if host in webworkers:
            ret['command_prefix'] = '%(virtualenv_root)s/bin/newrelic-admin run-program ' % env
            ret['supervisor_env_vars']['NEW_RELIC_CONFIG_FILE'] = '%(root)s/newrelic.ini' % env
            ret['supervisor_env_vars']['NEW_RELIC_ENVIRONMENT'] = current_env.get('deploy_env', '')

    if env.http_proxy:
        ret['supervisor_env_vars']['http_proxy'] = 'http://{}'.format(env.http_proxy)
        ret['supervisor_env_vars']['https_proxy'] = 'https://{}'.format(env.http_proxy)
        ret['supervisor_env_vars']['no_proxy'] = '{},{}'.format(','.join(all_hosts), env.get('additional_no_proxy_hosts', ''))

    for prop in important_props:
        ret[prop] = current_env.get(prop, '')

    ret['host_string'] = env.ccc_environment.get_hostname(env.host_string)
    ret['environment'] = current_env.get('deploy_env', '')

    if extra:
        ret.update(extra)
        if extra.get('celery_params') and extra['celery_params'].get('celery_loader'):
            ret['supervisor_env_vars']['CELERY_LOADER'] = extra['celery_params']['celery_loader']

    return json.dumps(ret)


@roles(ROLES_PILLOWTOP)
@parallel
def stop_pillows(current=False):
    code_root = env.code_current if current else env.code_root
    with cd(code_root):
        sudo('scripts/supervisor-group-ctl stop pillowtop')


@roles(ROLES_PILLOWTOP)
@parallel
def start_pillows(current=False):
    code_root = env.code_current if current else env.code_root
    with cd(code_root):
        sudo('scripts/supervisor-group-ctl start pillowtop')


@roles(ROLES_CELERY)
@parallel
def stop_celery_tasks(current=False):
    code_root = env.code_current if current else env.code_root
    with cd(code_root):
        sudo('scripts/supervisor-group-ctl stop celery')


@roles(ROLES_CELERY)
@parallel
def start_celery_tasks(current=False):
    code_root = env.code_current if current else env.code_root
    with cd(code_root):
        sudo('scripts/supervisor-group-ctl start celery')


@roles(set(ROLES_ALL_SERVICES) - set(ROLES_DJANGO))
@parallel
def restart_all_except_webworkers():
    _services_restart()


@roles(ROLES_STATIC)
def _decommission_host(host):
    files.comment(
        '/etc/nginx/sites-available/{}_commcare'.format(env.deploy_env),
        '^[ ]*server[ ]+{}'.format(host),
        use_sudo=True,
    )
    _check_and_reload_nginx()


@roles(ROLES_STATIC)
def _recommission_host(host):
    files.uncomment(
        '/etc/nginx/sites-available/{}_commcare'.format(env.deploy_env),
        'server[ ]+{}'.format(host),
        use_sudo=True,
    )
    _check_and_reload_nginx()


def _check_and_reload_nginx():
    sudo('nginx -t', shell=False, user='root')
    sudo('nginx -s reload', shell=False, user='root')


@contextmanager
def decommissioned_host(host):
    more_than_one_webworker = len(env.roledefs['django_app']) > 1

    if more_than_one_webworker:
        execute(_decommission_host, host)

    yield

    if more_than_one_webworker:
        execute(_recommission_host, host)


@roles(ROLES_DJANGO)
@serial
def restart_webworkers():
    with decommissioned_host(env.host):
        _services_restart()


@roles(ROLES_FORMPLAYER)
def restart_formplayer():
    _services_restart()


def _services_restart():
    """Stop and restart all supervisord services"""
    supervisor_command('stop all')

    supervisor_command('reread')
    supervisor_command('update')
    time.sleep(5)
    supervisor_command('start all')


def supervisor_command(command):
    sudo('supervisorctl %s' % (command), shell=False, user='root')
