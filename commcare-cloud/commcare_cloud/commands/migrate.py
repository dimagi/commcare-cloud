import jsonobject
import yaml
from couchdb_cluster_admin.utils import Config
from memoized import memoized_property

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


class CouchAllocationPlan(jsonobject.JsonObject):
    db_plans = jsonobject.ListProperty(lambda: ShardAllocationDoc)


class CouchMigration(object):
    def __init__(self, config_path, couch_conf_path, couch_plan_path):
        self.couch_plan_path = couch_plan_path
        self.couch_conf_path = couch_conf_path
        self.config_path = config_path

    @memoized_property
    def plan(self):
        with open(self.config_path) as f:
            config = yaml.load(f)

        return MigrationPlan.wrap(config)

    @memoized_property
    def couch_config(self):
        with open(self.couch_conf_path) as f:
            config = yaml.load(f)

        return Config.wrap(config)

    @memoized_property
    def couch_plan(self):
        with open(self.couch_plan_path) as f:
            plan = yaml.load(f)

        db_plans = [
            ShardAllocationDoc.from_plan_json(db_name, plan_json)
            for db_name, plan_json in plan.items()
        ]

        return CouchAllocationPlan(db_plans=db_plans)

    def validate_config(self, environment):
        self.plan.check(environment)

        destination_hosts = set(self.plan.couchdb2.get_destination_hosts(environment))
        for plan in self.couch_plan.db_plans:
            plan.validate_allocation()
            hosts = plan.get_host_list()
            assert not destination_hosts ^ set(hosts), (
                'Hosts referenced in migration config are different from '
                'those in CouchDB shard plan: {}'.format(destination_hosts ^ set(hosts))
            )
