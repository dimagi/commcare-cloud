from __future__ import absolute_import, print_function, unicode_literals

import collections
import csv
import inspect
import itertools
import json
import subprocess
import sys
from collections import defaultdict
from io import open
from operator import attrgetter, itemgetter

import yaml
from clint.textui import indent, puts
from couchdb_cluster_admin.utils import (
    Config,
    get_db_list,
    get_membership,
    get_shard_allocation,
)
from tabulate import tabulate

from commcare_cloud.colors import (
    color_added,
    color_changed,
    color_error,
    color_removed,
    color_success,
)
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.couch_utils import (
    get_cluster_shard_details,
    print_db_info,
    print_shard_table,
)
from commcare_cloud.commands.command_base import (
    Argument,
    CommandBase,
    CommandError,
)
from commcare_cloud.commands.inventory_lookup.getinventory import (
    get_instance_group,
)
from commcare_cloud.commands.inventory_lookup.inventory_lookup import (
    DjangoManage,
)
from commcare_cloud.commands.utils import PrivilegedCommand
from commcare_cloud.environment.exceptions import EnvironmentException
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.schemas.app_processes import get_machine_alias


class ListDatabases(CommandBase):
    command = 'list-postgresql-dbs'
    help = """

    Example:

    To list all database on a particular environment.

    ```
    commcare-cloud <env> list-postgresql-dbs
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
        dbs = environment.postgresql_config.to_generated_variables(environment)['postgresql_dbs']['all']
        for db in dbs:
            dbs_expected_on_host[db['host']].append(db['name'])
        return dbs_expected_on_host


class CeleryResourceReport(CommandBase):
    command = 'celery-resource-report'
    help = """
    Report of celery resources by queue.
    """

    arguments = (
        Argument('--show-workers', action='store_true', help=(
            "Includes the list of worker nodes for each queue"
        )),
        Argument('--csv', action='store_true', help=(
            "Output table as CSV"
        )),
    )

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

        headers = ['Pooling', 'Worker Queues', 'Processes', 'Concurrency', 'Avg Concurrency per worker']
        if args.show_workers:
            headers.append('Worker Hosts')
        rows = []
        for queue_name, stats in sorted(by_queue.items(), key=itemgetter(0)):
            workers = stats['num_workers']
            concurrency_ = stats['concurrency']
            row = [list(stats['pooling'])[0], '`{}`'.format(queue_name), workers, concurrency_, concurrency_ // workers]
            if args.show_workers:
                worker_hosts = stats['worker_hosts']
                row.append(','.join(sorted([get_machine_alias(environment, worker_host) for worker_host in worker_hosts])))
            rows.append(row)

        print_table(headers, rows, args.csv)


def print_table(headers, rows, output_csv=False):
    if output_csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        writer.writerows(rows)
    else:
        print(tabulate(rows, headers=headers, tablefmt='github'))


class PillowResourceReport(CommandBase):
    command = 'pillow-resource-report'
    help = """
    Report of pillow resources.
    """

    arguments = (
        Argument('--csv', action='store_true', help=(
            "Output table as CSV"
        )),
    )

    def run(self, args, manage_args):
        environment = get_environment(args.env_name)
        by_process = _get_pillow_resources_by_name(environment)

        headers = ['Pillow', 'Processes']
        rows = [
            [name, num_processes]
            for name, num_processes in sorted(by_process.items(), key=itemgetter(0))
        ]

        print_table(headers, rows, args.csv)


class PillowTopicAssignments(CommandBase):
    command = 'pillow-topic-assignments'
    help = """
    Print out the list of Kafka partitions assigned to each pillow process.
    """

    arguments = (
        Argument('pillow_name', help=(
            "Name of the pillow."
        )),
        Argument('--csv', action='store_true', help=(
            "Output as CSV"
        )),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        processes_per_pillow = _get_pillow_resources_by_name(environment)
        total_processes = processes_per_pillow[args.pillow_name]
        manage_args = ['pillow_topic_assignments', args.pillow_name, str(total_processes)]
        if args.csv:
            manage_args.append('--csv')
        args.release = None
        args.server = "django_manage[0]"
        args.tmux = None
        args.tee_file = None
        return DjangoManage(self.parser).run(args, manage_args)


def _get_pillow_resources_by_name(environment):
    pillows = environment.app_processes_config.pillows
    total_processes = defaultdict(int)
    for host, processes in pillows.items():
        for name, options in processes.items():
            total_processes[name] += options.num_processes
    return total_processes


class CouchDBClusterInfo(CommandBase):
    command = 'couchdb-cluster-info'
    help = inspect.cleandoc("""
    Output information about the CouchDB cluster.

    Shard counts are displayed as follows:
    * a single number if all nodes have the same count
    * the count on the first node followed by the difference in each following node
      e.g. 2000,+1,-2 indicates that the counts are 2000,2001,1998
    """)

    arguments = (
        Argument("--raw", action="store_true", help="Output raw shard allocations as YAML instead of printing tables."),
        Argument("--shard-counts", action="store_true", help="Include document counts for each shard"),
        Argument("--database", help="Only show output for this database"),
        Argument("--couch-port", default=15984, type=int, help="CouchDB port. Defaults to 15984"),
        Argument("--couch-local-port", default=15986, type=int, help="CouchDB node local port. Defaults to 15986"),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        couch_config = get_couch_config(environment, port=args.couch_port, local_port=args.couch_local_port)

        db_list = sorted(get_db_list(couch_config.get_control_node()))
        if args.database:
            if args.database not in db_list:
                raise CommandError("Database not present in cluster: {}".format(args.database))
            db_list = [args.database]

        shard_allocations = [get_shard_allocation(couch_config, db_name) for db_name in db_list]
        shard_details = []
        if args.shard_counts:
            shard_details = get_cluster_shard_details(couch_config, db_list)

        if args.raw:
            plan = {
                shard_allocation_doc.db_name: shard_allocation_doc.to_plan_json()
                for shard_allocation_doc in shard_allocations
            }
            if shard_details:
                shard_details = sorted(shard_details, key=attrgetter('db_name'))
                for db_name, shards in itertools.groupby(shard_details, key=attrgetter('db_name')):
                    by_node = defaultdict(list)
                    for shard_detail in shards:
                        by_node[shard_detail.node].append(shard_detail.to_json())
                    plan[db_name]["shard_details"] = by_node
            # hack - yaml didn't want to dump this directly
            yaml.safe_dump(json.loads(json.dumps(plan)), sys.stdout, indent=2)
            return 0

        if not args.database:
            puts('\nMembership')
            with indent():
                puts(get_membership(couch_config).get_printable())

        puts('\nDB Info')
        print_db_info(couch_config, db_list)

        puts('\nShard allocation')
        print_shard_table(shard_allocations, shard_details)
        return 0


def get_couch_config(environment, nodes=None, port=15984, local_port=15986):
    couch_nodes = nodes or environment.groups['couchdb2']
    config = Config(
        control_node_ip=couch_nodes[0],
        control_node_port=port,
        control_node_local_port=local_port,
        username=environment.get_secret('COUCH_USERNAME'),
        aliases={
            'couchdb@{}'.format(node): get_machine_alias(environment, node) for node in couch_nodes
        }
    )
    config.set_password(environment.get_secret('COUCH_PASSWORD'))
    return config


class UpdateLocalKnownHosts(CommandBase):
    command = 'update-local-known-hosts'
    help = (
        "Update the local known_hosts file of the environment configuration.\n\n"
        "You can run this on a regular basis to avoid having to `yes` through\n"
        "the ssh prompts. Note that when you run this, you are implicitly\n"
        "trusting that at the moment you run it, there is no man-in-the-middle\n"
        "attack going on, the type of security breech that the SSH prompt\n"
        "is meant to mitigate against in the first place."
    )

    arguments = (
        shared_args.LIMIT_ARG,
    )

    def run(self, args, unknown_args):
        limit = args.limit
        environment = get_environment(args.env_name)
        if limit:
            environment.inventory_manager.subset(limit)

        with open(environment.paths.known_hosts, 'r', encoding='utf-8') as known_hosts:
            original_keys_by_host = _get_host_key_map(
                [line.strip() for line in known_hosts.readlines()]
            )

        procs = {}
        for hostname in environment.inventory_hostname_map:
            port = '22'
            if ':' in hostname:
                hostname, port = hostname.split(':')
            cmd = 'ssh-keyscan -T 10 -p {port} {hostname},$(dig +short {hostname})'.format(
                hostname=hostname,
                port=port
            )
            procs[hostname] = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                               universal_newlines=True)

        lines = []
        error_hosts = set()
        for hostname, proc in procs.items():
            sys.stdout.write('[{}]: '.format(hostname))
            proc.wait()
            error, host_lines = _get_lines(proc)
            if error:
                sys.stdout.write(error)
            else:
                sys.stdout.write(str(color_success('fetched key\n')))
                lines.extend(host_lines)

        updated_keys_by_host = _get_host_key_map(lines)

        all_keys = set(original_keys_by_host) | set(updated_keys_by_host)
        lines = []
        for host_key_type in sorted(all_keys):
            host, key_type = host_key_type
            original = original_keys_by_host.pop(host_key_type, None)
            updated = updated_keys_by_host.get(host_key_type, None)
            if updated and original:
                if updated != original:
                    print(color_changed('Updating key: {} {}'.format(*host_key_type)))
            elif updated:
                print(color_added('Adding key: {} {}'.format(*host_key_type)))
            elif original:
                if limit or host in error_hosts:
                    # if we're limiting or there was an error keep original key
                    updated = original
                else:
                    print(color_removed('Removing key: {} {}'.format(*host_key_type)))

            if updated:
                lines.append('{} {} {}'.format(host, key_type, updated))

        with open(environment.paths.known_hosts, 'w', encoding='utf-8') as known_hosts:
            known_hosts.write('\n'.join(sorted(lines)))

        try:
            environment.check_known_hosts()
        except EnvironmentException as e:
            print(color_error(str(e)))
            return 1
        return 0


def _get_host_key_map(known_host_lines):
    """
    See https://man.openbsd.org/sshd.8#SSH_KNOWN_HOSTS_FILE_FORMAT
    :param known_host_lines: lines in known_hosts format
    :return: dict((hostname, key_type) -> key
    """
    keys_by_host = {}
    for line in known_host_lines:
        if not line:
            continue
        csv_hosts, key_type, key = line.split(' ')
        # filter out empty hosts ('[]:port' is empty host with non-standard port)
        hosts = [h for h in csv_hosts.split(',') if h and '[]' not in h]
        for host in hosts:
            keys_by_host[(host, key_type)] = key
    return keys_by_host


def _get_lines(proc):
    """Read lines from process stdout
    :returns tuple(error_message: AnyStr, lines: [AnyStr])
    To return a str, specify an encoding when creating the subprocess, otherwise bytes-like objects are returned
    """
    out = proc.stdout.read()
    if proc.returncode != 0:
        err = proc.stderr.read()
        return str(color_error('error: {}\n'.format(err))), []
    elif not out:
        return str(color_error('timeout\n')), []
    else:
        return None, out.splitlines()
