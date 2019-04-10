from __future__ import absolute_import
from __future__ import print_function
import time
from contextlib import contextmanager

from fabric.api import roles, parallel, env, sudo, serial, execute
from fabric.context_managers import cd
from fabric.contrib import files

from ..const import (
    ROLES_CELERY,
    ROLES_DJANGO,
    ROLES_FORMPLAYER,
    ROLES_PILLOWTOP,
    ROLES_STATIC,
    ROLES_ALL_SERVICES,
)


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


@roles(set(ROLES_ALL_SERVICES) - set(ROLES_DJANGO) - set(ROLES_FORMPLAYER))
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
