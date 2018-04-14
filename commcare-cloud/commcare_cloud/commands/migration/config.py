import os
from tempfile import gettempdir

import jsonobject
import yaml
from couchdb_cluster_admin.utils import Config
from memoized import memoized_property

from commcare_cloud.commands.inventory_lookup.getinventory import get_server_address
from commcare_cloud.environment.main import get_environment
from couchdb_cluster_admin.doc_models import ShardAllocationDoc

lazy_immutable_property = memoized_property

COUCH_SHARD_PLAN = 'shard_plan.yml'


class CouchMigration(object):
    def __init__(self, env_name, plan_path):
        self.plan_path = plan_path
        self.target_environment = get_environment(env_name)

    @memoized_property
    def plan(self):
        with open(self.plan_path) as f:
            plan = yaml.load(f)

        return CouchMigrationPlan.wrap(plan)

    @property
    def separate_source_and_target(self):
        return bool(self.plan.src_env)

    @property
    def all_environments(self):
        envs = [self.target_environment]
        if self.separate_source_and_target:
            envs.append(self.source_environment)
        return envs

    @property
    def source_environment(self):
        if self.separate_source_and_target:
            return get_environment(self.plan.src_env)
        return self.target_environment

    @memoized_property
    def source_couch_config(self):
        if not self.separate_source_and_target:
            return self.target_couch_config
        return self._get_couch_config(self.source_environment)

    @memoized_property
    def target_couch_config(self):
        return self._get_couch_config(self.target_environment)

    def _get_couch_config(self, environment):
        nodes = list(self.plan.allocation_by_node())
        error = '"get couch IP for env: {}'.format(environment.env_name)
        config = Config(
            control_node_ip=environment.groups['couchdb2'][0],
            control_node_port=15984,
            control_node_local_port=15986,
            username=environment.get_vault_var('localsettings_private.COUCH_USERNAME'),
            aliases={
                'couchdb@{}'.format(environment.translate_host(node, error)): node for node in nodes
            }
        )
        config.set_password(environment.get_vault_var('localsettings_private.COUCH_PASSWORD'))
        return config

    @lazy_immutable_property
    def working_dir(self):
        plan_name = os.path.splitext(os.path.basename(self.plan_path))[0]
        dirname = "migration_build_{}_{}".format(self.target_environment.env_name, plan_name)
        dir_path = os.path.join(os.path.dirname(self.plan_path), dirname)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return dir_path

    @memoized_property
    def couch_plan(self):
        with open(os.path.join(self.working_dir, COUCH_SHARD_PLAN)) as f:
            plan = yaml.load(f)

        return [
            ShardAllocationDoc.from_plan_json(db_name, plan_json)
            for db_name, plan_json in plan.items()
        ]


class CouchMigrationPlan(jsonobject.JsonObject):
    src_env = jsonobject.StringProperty()
    target_allocation = jsonobject.ListProperty()

    def allocation_by_node(self):
        return {
            node: int(copies)
            for nodes, copies in (group.split(':') for group in self.target_allocation)
            for node in nodes.split(',')
        }
