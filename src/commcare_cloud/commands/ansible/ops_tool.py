import collections
from collections import defaultdict
from operator import itemgetter

from clint.textui import puts, indent
from couchdb_cluster_admin.describe import print_shard_table
from couchdb_cluster_admin.suggest_shard_allocation import print_db_info
from couchdb_cluster_admin.utils import get_membership, get_shard_allocation, get_db_list, Config

from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.inventory_lookup.getinventory import get_instance_group
from commcare_cloud.commands.utils import PrivilegedCommand
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.schemas.app_processes import get_machine_alias


class ListDatabases(CommandBase):
    command = 'list-postgresql-dbs'
    help = """

    Example:

    To list all database on a particular environment.

    ```
    commcare-cloud <ev> list-databases
    ```
    """

    arguments = (
        Argument('--compare', action='store_true', help=(
            "Gives additional databases on the server."
        )),
    )

    def run(self, args, manage_args,compare=None):
        # Initialize variables
        dbs_expected_on_host = self.get_expected_dbs(args)  # Database that should be in host
        if args.compare:
            dbs_present_in_host = self.get_present_dbs(args)  # Database that are in host

        # Print Logic
        # Printing Comparison
        for host_address in dbs_expected_on_host.keys():
            print(host_address + ":")
            print(" " * 4 + "Expected Databases:")
            for database in dbs_expected_on_host[host_address]:
                print(" " * 8 + "- " + database)
            if args.compare:
                print(" " * 4 + "Additional Databases:")
                for database in dbs_present_in_host[host_address]:
                    if database not in dbs_expected_on_host[host_address]:
                        print(" " * 8 + "- " + database)

    @staticmethod
    def get_present_dbs( args):
        dbs_present_in_host = collections.defaultdict(list)
        args.server = 'postgresql'
        ansible_username = 'ansible'
        command = "python /usr/local/sbin/db-tools.py  --list-all"

        environment = get_environment(args.env_name)
        ansible_password = environment.get_ansible_user_password()
        host_addresses = get_instance_group(args.env_name, args.server)
        user_as = 'postgres'

        privileged_command = PrivilegedCommand(ansible_username, ansible_password, command, user_as)

        present_db_op = privileged_command.run_command(host_addresses)

        # List from Postgresql query.

        for host_address in present_db_op.keys():
            dbs_present_in_host[host_address] = present_db_op[host_address].split("\r\n")

        return dbs_present_in_host

    @staticmethod
    def get_expected_dbs(args):
        environment = get_environment(args.env_name)
        dbs_expected_on_host = collections.defaultdict(list)
        dbs = environment.postgresql_config.to_generated_variables()['postgresql_dbs']['all']
        for db in dbs:
            dbs_expected_on_host[db['host']].append(db['name'])
        return dbs_expected_on_host


class CeleryResourceReport(CommandBase):
    command = 'celery-resource-report'
    help = """
    Report of celery resources by queue.
    """

    arguments = ()

    def run(self, args, manage_args):
        environment = get_environment(args.env_name)
        celery_processes = environment.app_processes_config.celery_processes
        by_queue = defaultdict(lambda: {'num_workers': 0, 'concurrency': 0, 'pooling': set(), 'worker_hosts': set()})
        for host, queues in celery_processes.items():
            for queue_name, options in queues.items():
                queue = by_queue[queue_name]
                queue['num_workers'] += options.num_workers
                queue['concurrency'] += options.concurrency * options.num_workers
                queue['pooling'].add(options.pooling)
                queue['worker_hosts'].add(host)

        max_name_len = max([len(name) for name in by_queue])
        template = "{{:<8}} | {{:<{}}} | {{:<12}} | {{:<12}} | {{:<12}} | {{:<12}}".format(max_name_len + 2)
        print(template.format('Pooling', 'Worker Queues', 'Processes', 'Concurrency', 'Avg Concurrency per worker', 'Worker Hosts'))
        print(template.format('-------', '-------------', '---------', '-----------', '--------------------------', '------------'))
        for queue_name, stats in sorted(by_queue.items(), key=itemgetter(0)):
            workers = stats['num_workers']
            concurrency_ = stats['concurrency']
            worker_hosts = stats['worker_hosts']
            print(template.format(
                list(stats['pooling'])[0], '`{}`'.format(queue_name), workers, concurrency_, concurrency_ // workers,
                ','.join(sorted([get_machine_alias(environment, worker_host) for worker_host in worker_hosts]))
            ))


class PillowResourceReport(CommandBase):
    command = 'pillow-resource-report'
    help = """
    Report of pillow resources.
    """

    arguments = ()

    def run(self, args, manage_args):
        environment = get_environment(args.env_name)
        by_process = _get_pillow_resources_by_name(environment)
        _print_table(by_process)


def _get_pillow_resources_by_name(environment):
    pillows = environment.app_processes_config.pillows
    by_process = defaultdict(lambda: {'num_processes': 0, 'total_processes': None})
    for host, processes in pillows.items():
        for name, options in processes.items():
            config = by_process[name]
            config['num_processes'] += options.get('num_processes', 1)
    return by_process


def _print_table(by_process):
    max_name_len = max([len(name) for name in by_process])
    template = "{{:<{}}} | {{:<12}}".format(max_name_len + 2)
    print(template.format('Pillow', 'Processes'))
    print(template.format('------', '---------'))
    for queue_name, stats in sorted(by_process.items(), key=itemgetter(0)):
        workers = stats['num_processes']
        print(template.format(queue_name, workers))


class CouchDBClusterInfo(CommandBase):
    command = 'couchdb-cluster-info'
    help = "Output information about the CouchDB cluster"

    arguments = ()

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        couch_config = get_couch_config(environment)

        puts(u'\nMembership')
        with indent():
            puts(get_membership(couch_config).get_printable())

        puts(u'\nDB Info')
        print_db_info(couch_config)

        puts(u'\nShard allocation')
        print_shard_table([
            get_shard_allocation(couch_config, db_name)
            for db_name in sorted(get_db_list(couch_config.get_control_node()))
        ])
        return 0


def get_couch_config(environment, nodes=None):
    couch_nodes = nodes or environment.groups['couchdb2']
    config = Config(
        control_node_ip=couch_nodes[0],
        control_node_port=15984,
        control_node_local_port=15986,
        username=environment.get_vault_var('localsettings_private.COUCH_USERNAME'),
        aliases={
            'couchdb@{}'.format(node): get_machine_alias(environment, node) for node in couch_nodes
        }
    )
    config.set_password(environment.get_vault_var('localsettings_private.COUCH_PASSWORD'))
    return config
