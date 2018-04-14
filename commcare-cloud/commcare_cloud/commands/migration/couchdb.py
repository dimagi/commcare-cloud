import os
import subprocess

from clint.textui import puts, colored
from couchdb_cluster_admin.describe import print_shard_table
from couchdb_cluster_admin.file_plan import get_important_files
from couchdb_cluster_admin.suggest_shard_allocation import get_shard_allocation_from_plan
from couchdb_cluster_admin.utils import put_shard_allocation, get_shard_allocation, get_db_list, check_connection
from decorator import contextmanager
from six.moves import shlex_quote

from commcare_cloud.cli_utils import ask
from commcare_cloud.commands.ansible.helpers import AnsibleContext, run_action_with_check_mode
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commands.migration.config import CouchMigration
from commcare_cloud.commands.shared_args import arg_skip_check
from commcare_cloud.environment.main import get_environment


class MigrateCouchdb(CommandBase):
    command = 'migrate_couchdb'
    help = 'Perform a CouchDB migration'

    def make_parser(self):
        self.parser.add_argument(dest='migration_plan', help="Path to migration plan file")
        self.parser.add_argument(dest='couch_config', help="Path to couchdb config file")
        self.parser.add_argument(dest='couch_plan', help="Path to couchdb DB plan file")
        arg_skip_check(self.parser)

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()
        environment.get_ansible_vault_password()

        migration = CouchMigration(environment, args.migration_plan, args.couch_config, args.couch_plan)
        migration.validate_config()
        migration.couch_config.set_password('a')  # TODO
        check_connection(migration.couch_config.get_control_node())

        ansible_context = AnsibleContext(args)

        def run_check():
            return self._run_migration(environment, migration, ansible_context, check_mode=False)

        def run_apply():
            return self._run_migration(environment, migration, ansible_context, check_mode=False)

        return run_action_with_check_mode(run_check, run_apply, args.skip_check)

    def _run_migration(self, environment, migration, ansible_context, check_mode):
        rsync_files_by_host = prepare_to_sync_files(environment, migration, ansible_context, check_mode)

        with stop_couch(environment, ansible_context):
            with stop_couch(migration.plan.couchdb2.get_source_environment(), ansible_context):
                sync_files_to_dest(environment, migration, rsync_files_by_host, check_mode)

        commit_migration(migration)

        print_shard_table([
            get_shard_allocation(migration.couch_config, db_name)
            for db_name in sorted(get_db_list(migration.couch_config.get_control_node()))
        ])
        return 0


@contextmanager
def stop_couch(environment, ansible_context, check_mode=False):
    start_stop_service(environment, ansible_context, 'stopped', check_mode)
    yield
    start_stop_service(environment, ansible_context, 'started', check_mode)


def start_stop_service(environment, ansible_context, service_state, check_mode=False):
    for service in ('monit', 'couchdb2'):
        args = 'name={} state={}'.format(service, service_state)
        run_ansible_module(environment, ansible_context, 'couchdb2', 'service', args, True, None, check_mode)


def commit_migration(migration):
    shard_allocations = get_shard_allocation_from_plan(migration.couch_config, migration.couch_plan)
    for shard_allocation_doc in shard_allocations:
        response = put_shard_allocation(migration.couch_config, shard_allocation_doc)
        print(response)


def sync_files_to_dest(environment, migration, rsync_files_by_host, check_mode=True):
    extra_args = []
    if check_mode:
        extra_args.append('--check')

    for host, path in rsync_files_by_host.items():
        # TODO: get couch data dir from vars
        rsync_cmd = (
            "rsync -e 'ssh -oStrictHostKeyChecking=no' "
            "--append-verify -vaH --info=progress2 "
            "ansible@{source}:{couch_data_dir} {couch_data_dir} "
            "--files-from {file_list} -r {extra_args}"
        ).format(
            source=migration.plan.couchdb2.get_source_host(),
            couch_data_dir='/opt/data/couchdb2/',
            file_list=os.path.join('/tmp', os.path.basename(path)),
            extra_args='--dry-run' if check_mode else ''
        )
        # -S to receive password from stdin
        # -E to preserve agent forwarding env
        sudo_cmd = "sudo -SE -p '' {}".format(rsync_cmd)
        ssh_cmd = "ssh ansible@{} -A {}".format(host, shlex_quote(sudo_cmd))
        print(ssh_cmd)
        p = subprocess.Popen(ssh_cmd, stdin=subprocess.PIPE, shell=True)
        p.communicate(input='{}\n'.format(environment.get_ansible_user_password()))


def prepare_to_sync_files(environment, migration, ansible_context, check_mode=True):
    rsync_files_by_host = generate_rsync_lists(migration, check_mode)
    extra_args = []
    if check_mode:
        extra_args.append('--check')

    for host, path in rsync_files_by_host.items():
        copy_args = "src={src} dest={dest} owner={owner} group={group} mode={mode}".format(
            src=path,
            dest=os.path.join('/tmp', os.path.basename(path)),
            owner='couchdb',  # TODO: get from vars
            group='couchdb',
            mode='0644'
        )
        run_ansible_module(environment, ansible_context, host, 'copy', copy_args, True, None, *extra_args)
    return rsync_files_by_host


def generate_rsync_lists(migration, dry_run=False):
    full_plan = {plan.db_name: plan for plan in migration.couch_plan.db_plans}
    important_files_by_node = get_important_files(migration.couch_config, full_plan, validate_suffixes=not dry_run)
    paths_by_host = {}
    for node, file_list in important_files_by_node.items():
        files = sorted(file_list)
        path = os.path.join(migration.working_dir, '{}_files'.format(node))
        with open(path, 'w') as f:
            f.write('{}\n'.format('\n'.join(files)))

        paths_by_host[node.split('@')[1]] = path

    return paths_by_host
