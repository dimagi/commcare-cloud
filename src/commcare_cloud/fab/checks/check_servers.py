from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from fabric.api import roles, env, sudo, run, hide
from fabric.context_managers import cd
from fabric.decorators import runs_once

from ..const import (
    ROLES_ALL,
    ROLES_POSTGRESQL,
    ROLES_ELASTICSEARCH,
    ROLES_DEPLOY)


@roles(ROLES_ALL)
def ping():
    with hide('running', 'output'):
        hostname = run('hostname')
        vmballoon = run('vmware-toolbox-cmd stat balloon')
        vmswap = run('vmware-toolbox-cmd stat swap')
        uptime = run('uptime')
        free = run('free -h')
        print("===== Hello from %s =====" % hostname)
        print("[%s] %s" % (hostname, uptime))
        print("[%s] %s" % (hostname, free))
        print("[%s] vmware balloon: %s" % (hostname, vmballoon))
        print("[%s] vmware swap: %s" % (hostname, vmswap))
    #with hide('running'):

ELASTICSEARCH_CHECKED = False
@roles(ROLES_ELASTICSEARCH)
def elasticsearch():
    global ELASTICSEARCH_CHECKED
    if not ELASTICSEARCH_CHECKED:
        run("curl -XGET 'http://%s:9200/_cluster/health?pretty=true'" % env.host)
        ELASTICSEARCH_CHECKED = True
    run('service elasticsearch status')

@roles(ROLES_POSTGRESQL)
def postgresql():
    run('service postgresql status')
    run('service pgbouncer status')


@roles(ROLES_DEPLOY)
@runs_once
def perform_system_checks(current=False):
    path = env.code_current if current else env.code_root
    venv = env.py3_virtualenv_current if current else env.py3_virtualenv_root
    with cd(path):
        sudo('%s/bin/python manage.py check --deploy' % venv)
        sudo('%s/bin/python manage.py check --deploy -t database' % venv)
