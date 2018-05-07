"""
Migrate CouchDB

TODO:
* better cluster info. Include shard allocation + info from 'print_db_info' + size on disk
"""

import json
import os
from contextlib import contextmanager

import yaml
from clint.textui import puts, colored, indent
from couchdb_cluster_admin.describe import print_shard_table
from couchdb_cluster_admin.file_plan import get_important_files
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

RSYNC_FILE_LIST_NAME = 'couchdb_migration_rsync_file_list'


class MigrateCouchdb(CommandBase):
    command = 'migrate-couchdb'
    aliases = ('migrate_couchdb',)  # deprecated
    help = """
    Perform a CouchDB migration

    This is a recent and advanced addition to the capabilities,
    and is not yet ready for widespread use. At such a time as it is
    ready, it will be more thoroughly documented.
    """

    arguments = (
        Argument(dest='migration_plan', help="Path to migration plan file"),
        Argument(dest='action', choices=['describe', 'plan', 'migrate', 'commit'],
                 help="Action to perform."),
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
            # TODO: indent
            print_db_info(migration.target_couch_config)

            print u'\nShards'
            # TODO: indent
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
            return

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

        rsync_files_by_host = prepare_to_sync_files(migration, ansible_context)

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
    rsync_cmd = (
        "rsync -e 'ssh -oStrictHostKeyChecking=no' "
        "--append-verify -aH --info=progress2 "
        "ansible@{source}:{couch_data_dir} {couch_data_dir} "
        "--files-from {file_list} -r {extra_args}"
    ).format(
        source=migration.source_couch_config.control_node_ip,
        couch_data_dir='/opt/data/couchdb2/',
        file_list=os.path.join('/tmp', RSYNC_FILE_LIST_NAME),
        extra_args='--dry-run' if check_mode else ''
    )
    run_parallel_command(
        migration.target_environment,
        list(rsync_files_by_host),
        rsync_cmd
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

    for host, path in rsync_files_by_host.items():
        copy_args = "src={src} dest={dest} owner={owner} group={group} mode={mode}".format(
            src=path,
            dest=os.path.join('/tmp', RSYNC_FILE_LIST_NAME),
            owner='couchdb',  # TODO: get from vars
            group='couchdb',
            mode='0644'
        )
        run_ansible_module(
            migration.target_environment, ansible_context, host, 'copy', copy_args,
            True, None, False
        )
    return rsync_files_by_host


def generate_rsync_lists(migration, validate_suffixes=True):
    full_plan = {plan.db_name: plan for plan in migration.shard_plan}
    important_files_by_node = get_important_files(
        migration.source_couch_config, full_plan, validate_suffixes=validate_suffixes
    )
    paths_by_host = {}
    for node, file_list in important_files_by_node.items():
        files = sorted(file_list)
        path = os.path.join(migration.rsync_files_path, '{}_files'.format(node))
        with open(path, 'w') as f:
            f.write('{}\n'.format('\n'.join(files)))

        paths_by_host[node.split('@')[1]] = path

    return paths_by_host
