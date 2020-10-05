from __future__ import absolute_import
from __future__ import unicode_literals
import os

import jsonobject
import yaml
from couchdb_cluster_admin.doc_models import ShardAllocationDoc
from memoized import memoized_property

from commcare_cloud.commands.ansible.ops_tool import get_couch_config
from commcare_cloud.environment.main import get_environment

lazy_immutable_property = memoized_property

COUCH_SHARD_PLAN = 'shard_plan.yml'
PRUNE_PLAYBOOK_NAME = 'prune_couch_files.yml'


class CouchMigration(object):
    def __init__(self, environment, plan_path):
        self.plan_path = plan_path
        self.target_environment = environment

    @memoized_property
    def plan(self):
        with open(self.plan_path) as f:
            plan = yaml.safe_load(f)

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
        return get_couch_config(self.source_environment)

    @memoized_property
    def target_couch_config(self):
        error = '"get couch IP for env: {}'.format(self.target_environment.meta_config.deploy_env)
        nodes = [self.target_environment.translate_host(node, error) for node in list(self.plan.get_all_nodes())]
        return get_couch_config(self.target_environment, nodes)

    @lazy_immutable_property
    def working_dir(self):
        plan_name = os.path.splitext(os.path.basename(self.plan_path))[0]
        dirname = "migration_build_{}_{}".format(self.target_environment.meta_config.deploy_env, plan_name)
        dir_path = os.path.join(os.path.dirname(self.plan_path), dirname)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return dir_path

    @lazy_immutable_property
    def rsync_files_path(self):
        path = os.path.join(self.working_dir, '.rsync_files')
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @lazy_immutable_property
    def shard_plan_path(self):
        return os.path.join(self.working_dir, COUCH_SHARD_PLAN)

    @lazy_immutable_property
    def prune_playbook_path(self):
        return os.path.abspath(os.path.join(self.working_dir, PRUNE_PLAYBOOK_NAME))

    @memoized_property
    def shard_plan(self):
        with open(self.shard_plan_path) as f:
            plan = yaml.safe_load(f)

        return [
            ShardAllocationDoc.from_plan_json(db_name, plan_json)
            for db_name, plan_json in plan.items()
        ]

    @memoized_property
    def couchdb2_data_dir(self):
        hosts = self.target_environment.groups['couchdb2']
        encrypted_roots = {self.target_environment.get_host_vars(host).get('encrypted_root', '/opt/data') for host in hosts}
        assert len(encrypted_roots) == 1
        encrypted_root, = encrypted_roots
        return '{}/couchdb2/'.format(encrypted_root)


class CouchMigrationPlan(jsonobject.JsonObject):
    src_env = jsonobject.StringProperty()
    target_allocation = jsonobject.ListProperty()

    def get_all_nodes(self):
        return [
            node
            for nodes, _ in (group.split(':', 1) for group in self.target_allocation)
            for node in nodes.split(',')
        ]
