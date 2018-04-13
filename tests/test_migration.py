from __future__ import print_function

import os

from mock.mock import patch
from parameterized import parameterized

from commcare_cloud.commands.migration.config import CouchMigration
from commcare_cloud.commands.migration.couchdb import generate_rsync_lists
from commcare_cloud.environment.main import get_environment

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'migration_config')
TEST_ENVIRONMENTS = [
    dir for dir in os.listdir(TEST_ENVIRONMENTS_DIR)
    if os.path.isdir(os.path.join(TEST_ENVIRONMENTS_DIR, dir))
]


@parameterized(TEST_ENVIRONMENTS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_migration_config(env_name):
    _get_and_validate_migration(env_name)


def _get_and_validate_migration(env_name):
    env = get_environment(env_name)
    plan_path = os.path.join(env.paths.environments_dir, 'migration-plan.yml')
    couch_conf_path = os.path.join(env.paths.environments_dir, 'couch-config.yml')
    couch_plan_path = os.path.join(env.paths.environments_dir, 'shard-plan.yml')
    migration = CouchMigration(env, plan_path, couch_conf_path, couch_plan_path)
    migration.couch_config.set_password('a')  # TODO
    migration.validate_config()
    return migration


@parameterized(TEST_ENVIRONMENTS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_write_files(env_name):
    migration = _get_and_validate_migration(env_name)
    files_by_host = generate_rsync_lists(migration, dry_run=True)
    assert '10.247.164.75' in files_by_host
    assert '10.247.164.74' in files_by_host
    assert '10.247.164.76' in files_by_host

    with open(os.path.join(TEST_ENVIRONMENTS_DIR, 'expected_rsync_file.txt')) as exp:
        expected = exp.read()

    for host, file_path in files_by_host.items():
        with open(file_path, 'r') as f:
            actual = f.read()
        assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)
