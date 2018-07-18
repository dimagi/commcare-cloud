import json
import os
from collections import defaultdict
from contextlib import contextmanager

import yaml
from clint.textui import puts, colored, indent
from couchdb_cluster_admin.describe import print_shard_table
from couchdb_cluster_admin.file_plan import get_missing_files_by_node_and_source, get_node_files
from couchdb_cluster_admin.suggest_shard_allocation import get_shard_allocation_from_plan, generate_shard_allocation, \
    print_db_info
from couchdb_cluster_admin.utils import put_shard_allocation, get_shard_allocation, get_db_list, check_connection, \
    get_membership

from commcare_cloud.cli_utils import ask
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.ansible_playbook import run_ansible_playbook
from commcare_cloud.commands.ansible.helpers import AnsibleContext, run_action_with_check_mode
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.migrations.config import CouchMigration
from commcare_cloud.commands.migrations.files import MigrationFiles, prepare_migration_scripts
from commcare_cloud.commands.utils import render_template
from commcare_cloud.environment.main import get_environment

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

COUCHDB_RSYNC_SCRIPT = 'couchdb_rsync.sh'

RSYNC_FILE_LIST_FOLDER_NAME = 'couchdb_migration_rsync_file_list'


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
        Argument(dest='action', choices=['describe', 'plan', 'migrate', 'commit', 'clean'], help="""
            Action to perform

            - describe: Print out cluster info
            - plan: generate plan details from migration plan
            - migrate: stop nodes and copy shard data according to plan
            - commit: update database docs with new shard allocation
            - clean: remove shard files from hosts where they aren't needed
        """),
        shared_args.SKIP_CHECK_ARG,
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()

        migration = CouchMigration(environment, args.migration_plan)
        check_connection(migration.target_couch_config.get_control_node())
        if migration.separate_source_and_target:
            check_connection(migration.source_couch_config.get_control_node())

        ansible_context = AnsibleContext(args)

        if args.action == 'describe':
            return describe(migration)

        if args.action == 'plan':
            return plan(migration)

        if args.action == 'migrate':
            return migrate(migration, ansible_context, args.skip_check)

        if args.action == 'commit':
            return commit(migration)

        if args.actoin == 'clean':
            return clean(migration, ansible_context, args.skip_check)


def clean(migration, ansible_context, skip_check):
    nodes = generate_shard_prune_playbook(migration)
    if nodes:
        run_ansible_playbook(
            migration.target_environment, migration.prune_playbook_path, ansible_context,
            skip_check=skip_check
        )


def generate_shard_prune_playbook(migration):
    """Create a playbook for deleting unused files.
    :returns: List of nodes that have files to remove
    """
    full_plan = {plan.db_name: plan for plan in migration.shard_plan}
    _, deletable_files_by_node = get_node_files(migration.source_couch_config, full_plan)
    if not any(deletable_files_by_node.values()):
        return None

    deletable_files_by_node = {
        node.split('@')[1]: files
        for node, files in deletable_files_by_node.items()
        if files
    }
    prune_playbook = render_template('prune.yml.j2', {
        'deletable_files_by_node': deletable_files_by_node,
        'couch_data_dir': '/opt/data/couchdb2/'
    }, TEMPLATE_DIR)
    with open(migration.prune_playbook_path, 'w') as f:
        f.write(prune_playbook)

    return list(deletable_files_by_node)


def commit(migration):
    if ask("Are you sure you want to update the Couch Database config?"):
        commit_migration(migration)

        # TODO: verify that shard config in DB matches what we expect
        puts(colored.yellow("New shard allocation:\n"))
        print_shard_table([
            get_shard_allocation(migration.target_couch_config, db_name)
            for db_name in sorted(get_db_list(migration.target_couch_config.get_control_node()))
        ])
    return 0


def migrate(migration, ansible_context, skip_check):
    def run_check():
        return _run_migration(migration, ansible_context, check_mode=True)

    def run_apply():
        return _run_migration(migration, ansible_context, check_mode=False)

    return run_action_with_check_mode(run_check, run_apply, skip_check)


def plan(migration):
    new_plan = True
    if os.path.exists(migration.shard_plan_path):
        new_plan = ask("Plan already exists. Do you want to overwrite it?")
    if new_plan:
        shard_allocations = generate_shard_plan(migration)
    else:
        shard_allocations = migration.shard_plan
    print_shard_table([shard_allocation_doc for shard_allocation_doc in shard_allocations])
    return 0


def generate_shard_plan(migration):
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
    return shard_allocations


def describe(migration):
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


def _run_migration(migration, ansible_context, check_mode):
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


def generate_rsync_lists(migration):
    migration_file_configs = get_migration_file_configs(migration)
    for target_host, files_for_node in migration_file_configs.items():
        prepare_migration_scripts(target_host, files_for_node, migration.rsync_files_path)
    return list(migration_file_configs)


def get_migration_file_configs(migration):
    full_plan = {plan.db_name: plan for plan in migration.shard_plan}
    missing_files = get_missing_files_by_node_and_source(
        migration.source_couch_config, full_plan
    )
    migration_file_configs = {}
    for node, source_file_list in missing_files.items():
        target_host = node.split('@')[1]

        files_for_node = []
        for source, file_list in source_file_list.items():
            source_host = source.split('@')[1]
            files_for_node.append(
                MigrationFiles(
                    source_host=source_host,
                    source_dir='/opt/data/couchdb2/',
                    target_dir='/opt/data/couchdb2/',
                    files=[f.filename for f in file_list]
                )
            )

        if files_for_node:
            migration_file_configs[target_host] = files_for_node

    return migration_file_configs
