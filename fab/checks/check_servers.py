from fabric.api import roles, env, sudo, run, hide

from ..const import (
    ROLES_ALL,
    ROLES_POSTGRESQL,
    ROLES_ELASTICSEARCH,
    ROLES_RIAKCS,
)


@roles(ROLES_ALL)
def ping():
    with hide('running','output'):
        hostname = run('hostname')
        vmballoon = run('vmware-toolbox-cmd stat balloon')
        vmswap = run('vmware-toolbox-cmd stat swap')
        uptime = run('uptime')
        free = run('free -h')
        print("===== Hello from %s =====" % hostname)
        print("[%s] %s" % (hostname,uptime))
        print("[%s] %s" % (hostname,free))
        print("[%s] vmware balloon: %s" % (hostname,vmballoon))
        print("[%s] vmware swap: %s" % (hostname,vmswap))
    #with hide('running'):

ELASTICSEARCH_CHECKED = False
@roles(ROLES_ELASTICSEARCH)
def elasticsearch():
    global ELASTICSEARCH_CHECKED
    if not ELASTICSEARCH_CHECKED:
        run("curl -XGET 'http://%s:9200/_cluster/health?pretty=true'" % env.host)
        ELASTICSEARCH_CHECKED = True
    run('service elasticsearch status')

RIAKCS_CHECKED = False
@roles(ROLES_RIAKCS)
def riakcs():
    global RIAKCS_CHECKED
    if not RIAKCS_CHECKED:
        sudo("riak-admin cluster status")
        RIAKCS_CHECKED = True
    sudo('service riak status')
    sudo('service riak-cs status')

@roles(ROLES_POSTGRESQL)
def postgresql():
    run('service postgresql status')
    run('service pgbouncer status')
