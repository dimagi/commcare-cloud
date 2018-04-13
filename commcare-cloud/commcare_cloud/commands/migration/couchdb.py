import os

from couchdb_cluster_admin.file_plan import get_important_files

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commands.migration.config import CouchMigration
from commcare_cloud.environment.main import get_environment


class MigrateCouchdb(CommandBase):
    command = 'migrate_couch'
    help = 'Perform a CouchDB migration'

    def make_parser(self):
        self.parser.add_argument(dest='migration_plan', help="Path to migration plan file")
        self.parser.add_argument(dest='couch_config', help="Path to couchdb config file")
        self.parser.add_argument(dest='couch_plan', help="Path to couchdb DB plan file")

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        migration = CouchMigration(environment, args.migration_plan, args.couch_config, args.couch_plan)
        migration.validate_config()

        self.generate_rsync_list(migration)



    def generate_rsync_list(self, migration):
        full_plan = {plan.db_name: plan for plan in migration.couch_plan.db_plans}
        important_files_by_node = get_important_files(migration.couch_config, full_plan)
        for node, file_list in important_files_by_node.items():
            files = sorted(file_list)
            with open(os.path.join(migration.working_dir, '{}_files'.format(node)), 'w') as f:
                f.write('{}\n'.format('\n'.join(files)))
        """
        python couchdb-cluster-admin/file_plan.py important --conf icds.yml --from-plan couch-cluster.plan.json
        --node couch0 > couch0.files && scp couch0.files ansible@10.247.164.12:~/couch-rsync-file-list

        :param host:
        :return:
        """
