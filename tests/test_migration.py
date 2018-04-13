from __future__ import print_function

import os

import yaml
from parameterized import parameterized

from commcare_cloud.commands.migrate import CouchMigration
from commcare_cloud.environment.main import Environment
from commcare_cloud.environment.paths import DefaultPaths

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'migration_config')
TEST_ENVIRONMENTS = os.listdir(TEST_ENVIRONMENTS_DIR)


@parameterized(TEST_ENVIRONMENTS)
def test_migration_config(env_name):
    env = Environment(DefaultPaths(env_name, environments_dir=TEST_ENVIRONMENTS_DIR))

    plan_path = env.paths.get_env_file_path('migration-plan.yml')
    couch_conf_path = env.paths.get_env_file_path('couch-config.yml')
    couch_plan_path = env.paths.get_env_file_path('shard-plan.yml')
    migration = CouchMigration(plan_path, couch_conf_path, couch_plan_path)
    migration.validate_setup(env)
