import jsonobject
import yaml
from commcare_cloud.environment.main import get_environment
from couchdb_cluster_admin.doc_models import ShardAllocationDoc


class MigrationPlan(jsonobject.JsonObject):
    couchdb2 = jsonobject.ObjectProperty(lambda: CouchReshardMapping)

    def check(self, environment):
        self.couchdb2.check(environment)


class CouchReshardMapping(jsonobject.JsonObject):
    source = jsonobject.StringProperty()
    dest = jsonobject.ListProperty()

    def check(self, environment):
        self.get_source_host()
        self.get_destination_hosts(environment)

    def get_source_environment(self):
        env_name = self.source.split('.')[0]
        return get_environment(env_name)

    def get_source_host(self):
        host = self.source.split('.')[1]
        return self.get_source_environment().translate_host(host, 'couchdb migration configuration source host')

    def get_destination_hosts(self, environment):
        return [
            environment.translate_host(host, 'couchdb migration config destination hosts')
            for host in self.dest
        ]


def validate_setup(environment, migration_config_path, couch_shard_plan_path):
    with open(migration_config_path) as f:
        migration_config_json = yaml.load(f)

    migration_config = MigrationPlan.wrap(migration_config_json)
    migration_config.check(environment)

    with open(couch_shard_plan_path) as f:
        plan_json = yaml.load(f)

    plan_by_db = {
        db_name: ShardAllocationDoc.from_plan_json(db_name, plan_json)
        for db_name, plan_json in plan_json.items()
    }

    destination_hosts = set(migration_config.couchdb2.get_destination_hosts(environment))
    for db, plan in plan_by_db.items():
        plan.validate_allocation()
        hosts = plan.get_host_list()
        assert not destination_hosts ^ set(hosts), (
            'Hosts referenced in migration config are different from '
            'those in CouchDB shard plan: {}'.format(destination_hosts ^ set(hosts))
        )


