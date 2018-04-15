from __future__ import print_function

import os

import yaml
from mock.mock import patch
from nose_parameterized import parameterized

from commcare_cloud.commands.migrations.config import CouchMigration
from commcare_cloud.commands.migrations.couchdb import generate_rsync_lists
from commcare_cloud.environment.main import get_environment

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'migration_config')
PLANS_DIR = os.path.join(TEST_ENVIRONMENTS_DIR, 'plans')
TEST_PLANS = os.listdir(PLANS_DIR)

def tearDown():
    # delete generated files
    for plan_name in TEST_PLANS:
        plan_path = os.path.join(PLANS_DIR, plan_name)
        for item in os.listdir(plan_path):
            build_path = os.path.join(plan_path, item)
            if item.startswith('migration_build') and os.path.isdir(build_path):
                for file in os.listdir(build_path):
                    if file.startswith('couchdb@'):
                        os.remove(os.path.join(build_path, file))


@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_migration_plan(plan_name):
    plan_path = os.path.join(PLANS_DIR, plan_name, 'plan.yml')
    migration = CouchMigration(get_environment('env1'), plan_path)
    assert not migration.separate_source_and_target
    with open(os.path.join(PLANS_DIR, plan_name, 'expected_couch_config.yml')) as f:
        expected_couch_config_json = yaml.load(f)

    assert expected_couch_config_json == migration.target_couch_config.to_json()

    files_by_host = generate_rsync_lists(migration, validate_suffixes=False)

    with open(os.path.join(PLANS_DIR, plan_name, 'expected_rsync_file.txt')) as exp:
        expected = exp.read()

    for host, file_path in files_by_host.items():
        with open(file_path, 'r') as f:
            actual = f.read()
        assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)
