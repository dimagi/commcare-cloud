from __future__ import print_function

import os

from mock.mock import patch
from parameterized import parameterized

from commcare_cloud.commands.migrate import CouchMigration
from commcare_cloud.environment.main import get_environment

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'migration_config')
TEST_ENVIRONMENTS = [
    dir for dir in os.listdir(TEST_ENVIRONMENTS_DIR)
    if os.path.isdir(os.path.join(TEST_ENVIRONMENTS_DIR, dir))
]


@parameterized(TEST_ENVIRONMENTS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_migration_config(env_name):
    env = get_environment(env_name)

    plan_path = os.path.join(env.paths.environments_dir, 'migration-plan.yml')
    couch_conf_path = os.path.join(env.paths.environments_dir, 'couch-config.yml')
    couch_plan_path = os.path.join(env.paths.environments_dir, 'shard-plan.yml')
    migration = CouchMigration(plan_path, couch_conf_path, couch_plan_path)
    migration.validate_config(env)
