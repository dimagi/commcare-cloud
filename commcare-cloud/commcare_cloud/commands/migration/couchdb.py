import os

from couchdb_cluster_admin.file_plan import get_important_files

from commcare_cloud.commands.ansible.helpers import AnsibleContext
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

        migration = CouchMigration(environment, args.migration_plan, args.couch_config, args.couch_plan)
        migration.validate_config()
        migration.couch_config.set_password('a')  # TODO
        ansible_context = AnsibleContext(args)

        check_mode = True #not args.skip_check

        rsync_files_by_host = prepare_to_sync_files(environment, migration, ansible_context, check_mode)

        # TODO: stop couch nodes (and monit)
        sync_files_to_dest(environment, ansible_context, migration, rsync_files_by_host, check_mode)
        # TODO: start couch nodes (and monit)
        # TODO: commit plan
        """
        python couchdb-cluster-admin/suggest_shard_allocation.py --conf {config} --from-plan {plan} --commit
        """
        # TODO: validate setup
        """
        python couchdb-cluster-admin/describe.py --conf {config}
        """

def sync_files_to_dest(environment, ansible_context, migration, rsync_files_by_host, check_mode=True):
    extra_args = []
    if check_mode:
        extra_args.append('--check')

    for host, path in rsync_files_by_host.items():
        # TODO: get couch data dir from vars
        shell_command = (
            "rsync --append-verify -vaH --info=progress2 "
            "{source}:/opt/data/couchdb2/ /opt/data/couchdb2/ "
            "--files-from {file_list} -r"
        ).format(source=migration.plan.couchdb2.get_source_host(), file_list=path)
        run_ansible_module(environment, ansible_context, host, 'shell', shell_command, True, None, *extra_args)


def prepare_to_sync_files(environment, migration, ansible_context, check_mode=True):
    rsync_files_by_host = generate_rsync_lists(migration, check_mode)
    extra_args = []
    if check_mode:
        extra_args.append('--check')

    for host, path in rsync_files_by_host.items():
        copy_args = "src={src} dest={dest} owner={owner} group={group} mode={mode}".format(
            src=path,
            dest=path,
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
