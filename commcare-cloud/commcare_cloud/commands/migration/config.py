import os
from tempfile import gettempdir

import jsonobject
import yaml
from couchdb_cluster_admin.utils import Config
from memoized import memoized_property

from commcare_cloud.environment.main import get_environment
from couchdb_cluster_admin.doc_models import ShardAllocationDoc

lazy_immutable_property = memoized_property


class EnvironmentInjectionMixin(object):
    @property
    def environment(self):
        try:
            return self._environment
        except AttributeError:
            raise Exception('Environment not set')

    def set_environment(self, environment):
        if environment:
            self._environment = environment


class MigrationPlan(EnvironmentInjectionMixin, jsonobject.JsonObject):
    couchdb2 = jsonobject.ObjectProperty(lambda: CouchReshardMapping)

    def set_environment(self, environment):
        super(MigrationPlan, self).set_environment(environment)
        self.couchdb2.set_environment(environment)

    def check(self):
        self.environment  # check that it's set
        self.couchdb2.check()


class CouchReshardMapping(EnvironmentInjectionMixin, jsonobject.JsonObject):
    source = jsonobject.StringProperty()
    dest = jsonobject.ListProperty()

    def check(self):
        self.get_source_host()
        self.get_destination_hosts()

    def get_source_environment(self):
        env_name = self.source.split('.')[0]
        return get_environment(env_name)

    def get_source_host(self):
        host = self.source.split('.')[1]
        return self.get_source_environment().translate_host(host, 'couchdb migration configuration source host')

    def get_destination_hosts(self):
        return [
            self.environment.translate_host(host, 'couchdb migration config destination hosts')
            for host in self.dest
        ]


class CouchAllocationPlan(jsonobject.JsonObject):
    db_plans = jsonobject.ListProperty(lambda: ShardAllocationDoc)


class CouchMigration(object):
    def __init__(self, environment, config_path, couch_conf_path, couch_plan_path):
        self.environment = environment
        self.couch_plan_path = couch_plan_path
        self.couch_conf_path = couch_conf_path
        self.config_path = config_path

    @memoized_property
    def plan(self):
        with open(self.config_path) as f:
            config = yaml.load(f)

        plan = MigrationPlan.wrap(config)
        plan.set_environment(self.environment)
        return plan

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

    @lazy_immutable_property
    def working_dir(self):
        plan_name = os.path.split(os.path.basename(self.config_path))[0]
        dir = os.path.join(gettempdir(), self.environment.paths.env_name, plan_name)
        os.makedirs(dir)
        return dir

    def validate_config(self):
        self.plan.check()

        destination_hosts = set(self.plan.couchdb2.get_destination_hosts())
        for plan in self.couch_plan.db_plans:
            plan.validate_allocation()
            hosts = plan.get_host_list()
            assert destination_hosts <= set(hosts), (
                'Hosts referenced in migration config are not defined in '
                'CouchDB shard plan: {}'.format(destination_hosts - set(hosts))
            )


