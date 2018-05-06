import json
import os
from collections import defaultdict
from contextlib import contextmanager

import yaml
from clint.textui import puts, colored, indent
from couchdb_cluster_admin.describe import print_shard_table
from couchdb_cluster_admin.file_plan import get_missing_files_by_node_and_source
from couchdb_cluster_admin.suggest_shard_allocation import get_shard_allocation_from_plan, generate_shard_allocation, \
    print_db_info
from couchdb_cluster_admin.utils import put_shard_allocation, get_shard_allocation, get_db_list, check_connection, \
    get_membership

from commcare_cloud.cli_utils import ask
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import AnsibleContext, run_action_with_check_mode
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.migrations.config import CouchMigration
from commcare_cloud.environment.main import get_environment

COUCHDB_RSYNC_SCRIPT = 'couchdb_rsync.sh'

RSYNC_FILE_LIST_FOLDER_NAME = 'couchdb_migration_rsync_file_list'


class MigrateCouchdb(CommandBase):
    command = 'migrate-couchdb'
    aliases = ('migrate_couchdb',)  # deprecated
    help = 'Perform a CouchDB migration'

    arguments = (
        Argument(dest='migration_plan', help="Path to migration plan file"),
        Argument(dest='action', choices=['describe', 'plan', 'migrate', 'commit'],
                 help="Action to perform\n"
                      "    describe: Print out cluster info\n"
                      "    plan: generate plan details from migration plan\n"
                      "    migrate: stop nodes and copy shard data according to plan\n"
                      "    commit: update database docs with new shard allocation"),
        shared_args.SKIP_CHECK_ARG,
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()
        environment.get_ansible_vault_password()

        migration = CouchMigration(environment, args.migration_plan)
        check_connection(migration.target_couch_config.get_control_node())
        if migration.separate_source_and_target:
            check_connection(migration.source_couch_config.get_control_node())

        ansible_context = AnsibleContext(args)

        if args.action == 'describe':
            print u'\nMembership'
            with indent():
                puts(get_membership(migration.target_couch_config).get_printable())

            print u'\nDB Info'
            print_db_info(migration.target_couch_config)

            print u'\nShards'
            print_shard_table([
                get_shard_allocation(migration.target_couch_config, db_name)
                for db_name in sorted(get_db_list(migration.target_couch_config.get_control_node()))
            ])

            return 0

        if args.action == 'plan':
            new_plan = True
            if os.path.exists(migration.shard_plan_path):
                new_plan = ask("Plan already exists. Do you want to overwrite it?")

            if new_plan:
                shard_allocations = generate_shard_allocation(
                    migration.source_couch_config, migration.plan.target_allocation
                )

                with open(migration.shard_plan_path, 'w') as f:
                    plan = {
                        shard_allocation_doc.db_name: shard_allocation_doc.to_plan_json()
                        for shard_allocation_doc in shard_allocations
                    }
                    # hack - yaml didn't want to dump this directly
                    yaml.safe_dump(json.loads(json.dumps(plan)), f, indent=2)
            else:
                shard_allocations = migration.shard_plan

            print_shard_table([shard_allocation_doc for shard_allocation_doc in shard_allocations])
            return 0

        if args.action == 'migrate':
            def run_check():
                return self._run_migration(migration, ansible_context, check_mode=True)

            def run_apply():
                return self._run_migration(migration, ansible_context, check_mode=False)

            return run_action_with_check_mode(run_check, run_apply, args.skip_check)

        if args.action == 'commit':
            if ask("Are you sure you want to update the Couch Database config?"):
                commit_migration(migration)

                # TODO: verify that shard config in DB matches what we expect
                puts(colored.yellow("New shard allocation:\n"))
                print_shard_table([
                    get_shard_allocation(migration.target_couch_config, db_name)
                    for db_name in sorted(get_db_list(migration.target_couch_config.get_control_node()))
                ])

            return 0

    def _run_migration(self, migration, ansible_context, check_mode):
        puts(colored.blue('Give ansible user access to couchdb files:'))
        user_args = "user=ansible groups=couchdb append=yes"
        run_ansible_module(
            migration.source_environment, ansible_context, 'couchdb2', 'user', user_args,
            True, None, False
        )

        file_args = "path=/opt/data/couchdb2 mode=0755"
        run_ansible_module(
            migration.source_environment, ansible_context, 'couchdb2', 'file', file_args,
            True, None, False
        )

        puts(colored.blue('Copy file lists to nodes:'))
        rsync_files_by_host = prepare_to_sync_files(migration, ansible_context)

        puts(colored.blue('Stop couch and reallocate shards'))
        with stop_couch(migration.all_environments, ansible_context, check_mode):
            sync_files_to_dest(migration, rsync_files_by_host, check_mode)

        return 0


@contextmanager
def stop_couch(environments, ansible_context, check_mode=False):
    for env in environments:
        start_stop_service(env, ansible_context, 'stopped', check_mode)
    yield
    for env in environments:
        start_stop_service(env, ansible_context, 'started', check_mode)


def start_stop_service(environment, ansible_context, service_state, check_mode=False):
    extra_args = []
    if check_mode:
        extra_args.append('--check')

    for service in ('monit', 'couchdb2'):
        args = 'name={} state={}'.format(service, service_state)
        run_ansible_module(
            environment, ansible_context, 'couchdb2', 'service', args,
            True, None, False, *extra_args
        )


def commit_migration(migration):
    plan_by_db = {
        shard_allocation.db_name: shard_allocation
        for shard_allocation in migration.shard_plan
    }
    shard_allocations = get_shard_allocation_from_plan(
        migration.source_couch_config, plan_by_db, create=True
    )
    for shard_allocation_doc in shard_allocations:
        response = put_shard_allocation(migration.target_couch_config, shard_allocation_doc)
        print(response)


def sync_files_to_dest(migration, rsync_files_by_host, check_mode=True):
    file_root = os.path.join('/tmp', RSYNC_FILE_LIST_FOLDER_NAME)
    run_parallel_command(
        migration.target_environment,
        list(rsync_files_by_host),
        "{}{}".format(
            os.path.join(file_root, COUCHDB_RSYNC_SCRIPT),
            ' --dry-run' if check_mode else ''
        )
    )


def run_parallel_command(environment, hosts, command):
    from fabric.api import execute, sudo, env, parallel
    if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
        env.use_ssh_config = True
    env.forward_agent = True
    env.sudo_prefix = "sudo -SE -p '%(sudo_prompt)s' "
    env.user = 'ansible'
    env.password = environment.get_ansible_user_password()
    env.hosts = hosts
    env.warn_only = True

    @parallel(pool_size=10)
    def _task():
        sudo(command)

    execute(_task)


def prepare_to_sync_files(migration, ansible_context):
    rsync_files_by_host = generate_rsync_lists(migration)

    for host_ip in rsync_files_by_host:
        host_files_root = os.path.join(migration.rsync_files_path, host_ip)

        destination_path = os.path.join('/tmp', RSYNC_FILE_LIST_FOLDER_NAME)

        # remove destination path to ensure we're starting fresh
        file_args = "path={} state=absent".format(destination_path)
        run_ansible_module(
            migration.target_environment, ansible_context, host_ip, 'file', file_args,
            True, None, False
        )

        # recursively copy all rsync file lists to destination
        copy_args = "src={src}/ dest={dest} owner={owner} group={group} mode={mode}".format(
            src=host_files_root,
            dest=destination_path,
            owner='couchdb',  # TODO: get from vars
            group='couchdb',
            mode='0644'
        )
        run_ansible_module(
            migration.target_environment, ansible_context, host_ip, 'copy', copy_args,
            True, None, False
        )

        # make script executable
        file_args = "path={path} mode='0744'".format(
            path=os.path.join(destination_path, COUCHDB_RSYNC_SCRIPT)
        )
        run_ansible_module(
            migration.target_environment, ansible_context, host_ip, 'file', file_args,
            True, None, False
        )
    return rsync_files_by_host


def _render_template(name, context):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    ))
    return env.get_template(name).render(context)


def generate_rsync_lists(migration):
    full_plan = {plan.db_name: plan for plan in migration.shard_plan}
    missing_files = get_missing_files_by_node_and_source(
        migration.source_couch_config, full_plan
    )
    paths_by_host = defaultdict(list)
    for node, source_file_list in missing_files.items():
        node_ip = node.split('@')[1]
        node_files_path = os.path.join(migration.rsync_files_path, node_ip)
        if not os.path.exists(node_files_path):
            os.makedirs(node_files_path)

        files_for_node = []
        for source, file_list in source_file_list.items():
            source_ip = source.split('@')[1]
            files = sorted([f.filename for f in file_list])
            filename = '{}__files'.format(source_ip)
            path = os.path.join(node_files_path, filename)
            with open(path, 'w') as f:
                f.write('{}\n'.format('\n'.join(files)))

            files_for_node.append((source_ip, filename))
            paths_by_host[node_ip].append(path)

        if files_for_node:
            # create rsync script
            rsync_script = _render_template('couchdb_rsync.sh.j2', {
                'rsync_file_list': files_for_node,
                'couch_data_dir': '/opt/data/couchdb2/',
                'rsync_file_root': os.path.join('/tmp', RSYNC_FILE_LIST_FOLDER_NAME)
            })
            with open(os.path.join(node_files_path, COUCHDB_RSYNC_SCRIPT), 'w') as f:
                f.write(rsync_script)

    return paths_by_host
