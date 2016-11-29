import os
import json
import yaml
import time
import posixpath
from contextlib import contextmanager

from ansible.inventory import InventoryParser
from fabric.api import roles, parallel, env, sudo, serial, execute
from fabric.colors import red, magenta
from fabric.context_managers import cd
from fabric.contrib import files

from ..const import (
    ROLES_CELERY,
    ROLES_DJANGO,
    ROLES_TOUCHFORMS,
    ROLES_FORMPLAYER,
    ROLES_SMS_QUEUE,
    ROLES_REMINDER_QUEUE,
    ROLES_PILLOW_RETRY_QUEUE,
    ROLES_PILLOWTOP,
    ROLES_STATIC,
    ROLES_ALL_SERVICES,
)
from fabric import utils
from ..utils import execute_with_timing, get_pillow_env_config, is_monolith


def set_supervisor_config():
    """Upload and link Supervisor configuration from the template."""
    execute_with_timing(set_celery_supervisorconf)
    execute_with_timing(set_djangoapp_supervisorconf)
    execute_with_timing(set_errand_boy_supervisorconf)
    execute_with_timing(set_formsplayer_supervisorconf)
    execute_with_timing(set_formplayer_spring_supervisorconf)
    execute_with_timing(set_pillowtop_supervisorconf)
    execute_with_timing(set_sms_queue_supervisorconf)
    execute_with_timing(set_reminder_queue_supervisorconf)
    execute_with_timing(set_pillow_retry_queue_supervisorconf)
    execute_with_timing(set_websocket_supervisorconf)

    # if needing tunneled ES setup, comment this back in
    # execute(set_elasticsearch_supervisorconf)


def _get_celery_queues():
    host = env.get('host_string')
    if host and '.' in host:
        host = host.split('.')[0]

    queues = env.celery_processes.get('*', {})
    host_queues = env.celery_processes.get(host, {})
    queues.update(host_queues)

    return queues


@roles(ROLES_CELERY)
@parallel
def set_celery_supervisorconf():

    conf_files = {
        'main':                         ['supervisor_celery_main.conf'],
        'periodic':                     ['supervisor_celery_beat.conf', 'supervisor_celery_periodic.conf'],
        'sms_queue':                    ['supervisor_celery_sms_queue.conf'],
        'reminder_queue':               ['supervisor_celery_reminder_queue.conf'],
        'reminder_rule_queue':          ['supervisor_celery_reminder_rule_queue.conf'],
        'reminder_case_update_queue':   ['supervisor_celery_reminder_case_update_queue.conf'],
        'pillow_retry_queue':           ['supervisor_celery_pillow_retry_queue.conf'],
        'background_queue':             ['supervisor_celery_background_queue.conf'],
        'saved_exports_queue':          ['supervisor_celery_saved_exports_queue.conf'],
        'ucr_queue':                    ['supervisor_celery_ucr_queue.conf'],
        'email_queue':                  ['supervisor_celery_email_queue.conf'],
        'repeat_record_queue':          ['supervisor_celery_repeat_record_queue.conf'],
        'logistics_reminder_queue':     ['supervisor_celery_logistics_reminder_queue.conf'],
        'logistics_background_queue':   ['supervisor_celery_logistics_background_queue.conf'],
        'async_restore_queue':          ['supervisor_celery_async_restore_queue.conf'],
        'flower':                       ['supervisor_celery_flower.conf'],
    }

    queues = _get_celery_queues()
    if 'periodic' in queues and env.host != queues['periodic'].get('server_whitelist'):
        show_periodic_server_whitelist_message_and_abort(env)
    _rebuild_supervisor_conf_file('make_supervisor_conf', 'celery_bash_runner.sh')
    for queue, params in queues.items():
        for config_file in conf_files[queue]:
            _rebuild_supervisor_conf_file('make_supervisor_conf', config_file, {'celery_params': params})


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
        '   {environment}.celery_processes.{hostname}.periodic\n'
        '   from fab/environments.yml\n'
        "2. know what you're doing and want to deploy celery beat to {environment}\n"
        "   set {environment}.celery_processes.{hostname}.periodic.server_whitelist\n"
        '   to {host}\n'
        '   in fab/environments.yml\n'
        "3. are really confused, find someone who might know more about this\n"
        "   and ask them."
        .format(environment=env.environment,
                hostname=env.get('host_string').split('.')[0],
                host=env.host)
        )


@roles(ROLES_PILLOWTOP)
@parallel
def set_pillowtop_supervisorconf():
    # Don't run if there are no hosts for the 'django_pillowtop' role.
    # If there are no matching roles, it's still run once
    # on the 'deploy' machine, db!
    # So you need to explicitly test to see if all_hosts is empty.
    if env.all_hosts:
        _rebuild_supervisor_conf_file(
            'make_supervisor_pillowtop_conf',
            'supervisor_pillowtop.conf',
            {'pillow_env_configs': filter(None, [
                get_pillow_env_config(environment)
                for environment in ['default', env.environment]
            ])}
        )
        _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_form_feed.conf')


@roles(ROLES_DJANGO)
@parallel
def set_djangoapp_supervisorconf():
    _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_django.conf')


@roles(ROLES_DJANGO)
@parallel
def set_errand_boy_supervisorconf():
    _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_errand_boy.conf')


@roles(ROLES_TOUCHFORMS)
@parallel
def set_formsplayer_supervisorconf():
    _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_formsplayer.conf')


@roles(ROLES_FORMPLAYER)
def set_formplayer_spring_supervisorconf():
    _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_formplayer_spring.conf')


@roles(ROLES_SMS_QUEUE)
@parallel
def set_sms_queue_supervisorconf():
    if 'sms_queue' in _get_celery_queues():
        _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_sms_queue.conf')


@roles(ROLES_REMINDER_QUEUE)
@parallel
def set_reminder_queue_supervisorconf():
    if 'reminder_queue' in _get_celery_queues():
        _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_reminder_queue.conf')


@roles(ROLES_PILLOW_RETRY_QUEUE)
@parallel
def set_pillow_retry_queue_supervisorconf():
    if 'pillow_retry_queue' in _get_celery_queues():
        _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_pillow_retry_queue.conf')


@roles(ROLES_STATIC)
@parallel
def set_websocket_supervisorconf():
    _rebuild_supervisor_conf_file('make_supervisor_conf', 'supervisor_websockets.conf')


def _rebuild_supervisor_conf_file(conf_command, filename, params=None):
    sudo('mkdir -p {}'.format(posixpath.join(env.services, 'supervisor')))

    if filename in env.get('service_blacklist', []):
        print magenta('Skipping {} because the service has been blacklisted'.format(filename))
        return

    with cd(env.code_root):
        sudo((
            '%(virtualenv_root)s/bin/python manage.py '
            '%(conf_command)s --traceback --conf_file "%(filename)s" '
            '--conf_destination "%(destination)s" --params \'%(params)s\''
        ) % {

            'conf_command': conf_command,
            'virtualenv_root': env.virtualenv_root,
            'filename': filename,
            'destination': posixpath.join(env.services, 'supervisor'),
            'params': _format_env(env, params)
        })


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
        'environment',
        'code_root',
        'code_current',
        'log_dir',
        'sudo_user',
        'host_string',
        'project',
        'es_endpoint',
        'jython_home',
        'virtualenv_root',
        'virtualenv_current',
        'django_port',
        'django_bind',
        'flower_port',
        'jython_memory',
        'formplayer_memory'
    ]

    host = current_env.get('host_string')
    inventory_groups = InventoryParser(current_env.inventory).groups.values()
    newrelic_machines = [machine.name
                         for group in inventory_groups for machine in group.hosts
                         if 'newrelic_app_name' in group.vars]
    if host in newrelic_machines:
        ret['new_relic_command'] = '%(virtualenv_root)s/bin/newrelic-admin run-program ' % env
        ret['supervisor_env_vars'] = {
            'NEW_RELIC_CONFIG_FILE': '%(root)s/newrelic.ini' % env,
            'NEW_RELIC_ENVIRONMENT': '%(environment)s' % env
        }
    else:
        ret['new_relic_command'] = ''
        ret['supervisor_env_vars'] = []

    for prop in important_props:
        ret[prop] = current_env.get(prop, '')

    if extra:
        ret.update(extra)

    return json.dumps(ret)


@roles(ROLES_PILLOWTOP)
def stop_pillows(current=False):
    code_root = env.code_current if current else env.code_root
    with cd(code_root):
        sudo('scripts/supervisor-group-ctl stop pillowtop')


@roles(ROLES_PILLOWTOP)
def start_pillows(current=False):
    code_root = env.code_current if current else env.code_root
    with cd(code_root):
        sudo('scripts/supervisor-group-ctl start pillowtop')


@roles(ROLES_CELERY)
@parallel
def stop_celery_tasks():
    with cd(env.code_root):
        sudo('scripts/supervisor-group-ctl stop celery')


@roles(set(ROLES_ALL_SERVICES) - set(ROLES_DJANGO))
@parallel
def restart_all_except_webworkers():
    _services_restart()


@roles(ROLES_STATIC)
def _decommission_host(host):
    files.comment(
        '/etc/nginx/sites-available/{}_commcare'.format(env.environment),
        '^[ ]*server[ ]+{}'.format(host),
        use_sudo=True,
    )
    _check_and_reload_nginx()


@roles(ROLES_STATIC)
def _recommission_host(host):
    files.uncomment(
        '/etc/nginx/sites-available/{}_commcare'.format(env.environment),
        'server[ ]+{}'.format(host),
        use_sudo=True,
    )
    _check_and_reload_nginx()


def _check_and_reload_nginx():
    sudo('nginx -t', shell=False, user='root')
    sudo('nginx -s reload', shell=False, user='root')


@contextmanager
def decommissioned_host(host):
    not_monolith = not is_monolith()
    if not_monolith:
        execute(_decommission_host, host)

    yield

    if not_monolith:
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

    supervisor_command('update')
    supervisor_command('reload')
    time.sleep(5)
    supervisor_command('start all')


def supervisor_command(command):
    sudo('supervisorctl %s' % (command), shell=False, user='root')
