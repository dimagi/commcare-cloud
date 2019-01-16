import difflib
import json
import os
from collections import defaultdict
from contextlib import contextmanager

import yaml
from clint.textui import puts, colored, indent
from couchdb_cluster_admin.describe import print_shard_table
from couchdb_cluster_admin.doc_models import ShardAllocationDoc
from couchdb_cluster_admin.file_plan import get_missing_files_by_node_and_source, get_node_files, \
    figure_out_what_you_can_and_cannot_delete
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
from commcare_cloud.commands.migrations.copy_files import SourceFiles, prepare_file_copy_scripts, REMOTE_MIGRATION_ROOT, \
    FILE_MIGRATION_RSYNC_SCRIPT, copy_scripts_to_target_host, execute_file_copy_scripts
from commcare_cloud.commands.utils import render_template
from commcare_cloud.environment.main import get_environment

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
PLAY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plays')


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
        shared_args.LIMIT_ARG,
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()

        migration = CouchMigration(environment, args.migration_plan)
        check_connection(migration.target_couch_config.get_control_node())
        if migration.separate_source_and_target:
            check_connection(migration.source_couch_config.get_control_node())

        ansible_context = AnsibleContext(args)
        if args.limit and args.action != 'clean':
            puts(colored.yellow('Ignoring --limit (it only applies to "clean" action).'))

        if args.action == 'describe':
            return describe(migration)

        if args.action == 'plan':
            return plan(migration)

        if args.action == 'migrate':
            return migrate(migration, ansible_context, args.skip_check)

        if args.action == 'commit':
            return commit(migration, ansible_context)

        if args.action == 'clean':
            return clean(migration, ansible_context, args.skip_check, args.limit)


def clean(migration, ansible_context, skip_check, limit):
    diff_with_db = diff_plan(migration)
    if diff_with_db:
        puts(colored.red("Current plan differs with database:\n"))
        puts("{}\n\n".format(diff_with_db))
        puts(
            "This could mean that the plan hasn't been committed yet\n"
            "or that the plan was re-generated.\n"
            "Performing the 'clean' operation is still safe but may\n"
            "not have the outcome you are expecting.\n"
        )
        if not ask("Do you wish to continue?"):
            puts(colored.red('Abort.'))
            return 0

    alloc_docs_by_db = get_db_allocations(migration.target_couch_config)
    puts(colored.yellow("Checking shards on disk vs DB. Please wait."))
    if not assert_files(migration, alloc_docs_by_db, ansible_context):
        puts(colored.red("Not all couch files are accounted for. Aborting."))
        return 1

    nodes = generate_shard_prune_playbook(migration)
    if nodes:
        return run_ansible_playbook(
            migration.target_environment, migration.prune_playbook_path, ansible_context,
            skip_check=skip_check,
            limit=limit
        )


def get_db_allocations(couch_config):
    return {
        db_name: get_shard_allocation(couch_config, db_name)
        for db_name in sorted(get_db_list(couch_config.get_control_node()))
    }


def diff_plan(migration):
    plan_dbs = {doc.db_name for doc in migration.shard_plan}
    db_allocations = [
        doc
        for db_name, doc in get_db_allocations(migration.target_couch_config).items()
        if db_name in plan_dbs
    ]
    l1 = get_shard_table(_get_aliased_allocation_docs(migration))
    l2 = get_shard_table(db_allocations)
    difflines = list(difflib.ndiff(l1, l2))
    has_diff = any(d for d in difflines if d[0] in '+-')
    if has_diff:
        return '\n'.join(difflines)


def generate_shard_prune_playbook(migration):
    """Create a playbook for deleting unused files.
    :returns: List of nodes that have files to remove
    """
    # get shard allocation from DB directly instead of using plan in case they are different
    full_plan = get_db_allocations(migration.target_couch_config)
    shard_suffix_by_db = {
        db_name: shard_allocation_doc.usable_shard_suffix
        for db_name, shard_allocation_doc in full_plan.items()
    }
    _, deletable_files_by_node = figure_out_what_you_can_and_cannot_delete(full_plan, shard_suffix_by_db)
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


def commit(migration, ansible_context):
    alloc_docs_by_db = {plan.db_name: plan for plan in migration.shard_plan}
    puts(colored.yellow("Checking shards on disk vs plan. Please wait."))
    if not assert_files(migration, alloc_docs_by_db, ansible_context):
        puts(colored.red("Some shard files are not where we expect. Have you run 'migrate'?"))
        puts(colored.red("Aborting"))
        return 1
    else:
        puts(colored.yellow("All shards appear to be where we expect according to the plan."))

    if ask("Are you sure you want to update the Couch Database config?"):
        commit_migration(migration)

        diff_with_db = diff_plan(migration)
        if diff_with_db:
            puts(colored.red('DB allocation differs from expected:\n'))
            puts("{}\n\n".format(diff_with_db))
            puts("Check the DB state and logs and maybe try running 'commit' again?")
            return 1

        puts(colored.yellow("New shard allocation:\n"))
        print_shard_table([
            get_shard_allocation(migration.target_couch_config, db_name)
            for db_name in sorted(get_db_list(migration.target_couch_config.get_control_node()))
        ])
    return 0


def assert_files(migration, alloc_docs_by_db, ansible_context):
    files_by_node = get_files_for_assertion(alloc_docs_by_db)
    expected_files_vars = os.path.abspath(os.path.join(migration.working_dir, 'assert_vars.yml'))
    with open(expected_files_vars, 'w') as f:
        yaml.safe_dump({'files_by_node': files_by_node}, f, indent=2)

    play_path = os.path.join(PLAY_DIR, 'assert_couch_files.yml')
    with ansible_context.with_vars({ansible_context.stdout_callback: 'minimal'}):
        return_code = run_ansible_playbook(
            migration.target_environment, play_path, ansible_context,
            always_skip_check=True,
            quiet=True,
            unknown_args=['-e', '@{}'.format(expected_files_vars)]
        )
    return return_code == 0


def migrate(migration, ansible_context, skip_check):
    print_allocation(migration)
    if not ask("Continue with this plan?"):
        puts("Abort")
        return 0

    def run_check():
        return _run_migration(migration, ansible_context, check_mode=True)

    def run_apply():
        return _run_migration(migration, ansible_context, check_mode=False)

    return run_action_with_check_mode(run_check, run_apply, skip_check)


def print_allocation(migration):
    printable_docs = _get_aliased_allocation_docs(migration)
    print_shard_table(printable_docs)


def _get_aliased_allocation_docs(migration):
    def convert_to_aliases(nodes):
        return [
            migration.target_couch_config.aliases.get(node, node)
            for node in nodes
        ]

    printable_docs = []
    for doc in migration.shard_plan:
        doc_json = doc.to_plan_json()
        doc_json['by_range'] = {
            shard: convert_to_aliases(by_range)
            for shard, by_range in doc_json['by_range'].items()
        }
        printable_docs.append(ShardAllocationDoc.from_plan_json(doc.db_name, doc_json))
    return printable_docs


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
    puts(u'\nMembership')
    with indent():
        puts(get_membership(migration.target_couch_config).get_printable())
    puts(u'\nDB Info')
    print_db_info(migration.target_couch_config)

    puts(u'\nShard allocation')
    diff_with_db = diff_plan(migration)
    if diff_with_db:
        puts(colored.yellow('DB allocation differs from plan:\n'))
        puts("{}\n\n".format(diff_with_db))
    else:
        puts(colored.green('DB allocation matches plan.'))
        print_shard_table([
            get_shard_allocation(migration.target_couch_config, db_name)
            for db_name in sorted(get_db_list(migration.target_couch_config.get_control_node()))
        ])
    return 0


def get_files_for_assertion(alloc_docs_by_db):
    files_by_nodes = {}
    shard_suffix_by_db = {
        db_name: shard_allocation_doc.usable_shard_suffix
        for db_name, shard_allocation_doc in alloc_docs_by_db.items()
    }
    files_by_node, _ = figure_out_what_you_can_and_cannot_delete(alloc_docs_by_db, shard_suffix_by_db)
    for node, files in files_by_node.items():
        node_ip = node.split('@')[1]
        files_by_nodes[node_ip] = {
            'views': [
                node_file.filename for node_file in files if node_file.filename.endswith('design')
            ],
            'shards': [
                node_file.filename for node_file in files if node_file.filename.endswith('.couch')
            ]
        }
    return files_by_nodes


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
        execute_file_copy_scripts(migration.target_environment, list(rsync_files_by_host), check_mode)

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


def prepare_to_sync_files(migration, ansible_context):
    rsync_files_by_host = generate_rsync_lists(migration)

    for host_ip in rsync_files_by_host:
        copy_scripts_to_target_host(
            host_ip,
            migration.rsync_files_path,
            migration.target_environment,
            ansible_context
        )
    return rsync_files_by_host


def generate_rsync_lists(migration):
    migration_file_configs = get_migration_file_configs(migration)
    for target_host, files_for_node in migration_file_configs.items():
        prepare_file_copy_scripts(target_host, files_for_node, migration.rsync_files_path)
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
                SourceFiles(
                    source_host=source_host,
                    source_dir='/opt/data/couchdb2/',
                    target_dir='/opt/data/couchdb2/',
                    files=[f.filename for f in file_list]
                )
            )

        if files_for_node:
            migration_file_configs[target_host] = files_for_node

    return migration_file_configs


def get_shard_table(shard_allocation_docs):
    lines = []
    last_header = None
    db_names = [shard_allocation_doc.db_name for shard_allocation_doc in shard_allocation_docs]
    max_db_name_len = max(map(len, db_names))
    for shard_allocation_doc in sorted(shard_allocation_docs, key=lambda doc: doc.db_name):
        this_header = sorted(shard_allocation_doc.by_range)
        change_header = (last_header != this_header)
        lines.append(shard_allocation_doc.get_printable(include_shard_names=change_header, db_name_len=max_db_name_len))
        last_header = this_header
    return lines
