from __future__ import print_function

import collections

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment


class ListDbs(CommandBase):
    command = 'list-dbs'
    help = """
        List out databases by host
    """

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        dbs = environment.postgresql_config.to_generated_variables()['postgresql_dbs']['all']
        dbs_by_host = collections.defaultdict(list)
        for db in dbs:
            dbs_by_host[db['host']].append(db['name'])

        db_standby_by_host = collections.defaultdict(list)
        for standby in environment.groups['pg_standby']:
            if 'hot_standby_master' in environment.get_host_vars(standby):
                db_standby_by_host[environment.get_host_vars(standby)['hot_standby_master']].append(standby)

        for host, db_names in sorted(dbs_by_host.items()):
            standby_hostnames = sorted(environment.get_hostname(standby).split('.')[0]
                                 for standby in db_standby_by_host[host])
            hostname = environment.get_hostname(host).split('.')[0]
            if not standby_hostnames:
                print(hostname)
            else:
                print('{} ({})'.format(hostname, ', '.join(standby_hostnames)))
            for db_name in sorted(db_names):
                print(' ', db_name)
