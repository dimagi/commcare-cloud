from __future__ import print_function

import os
import shutil

import yaml
from couchdb_cluster_admin.doc_models import ShardAllocationDoc
from mock.mock import patch
from nose_parameterized import parameterized

from commcare_cloud.commands.migrations.config import CouchMigration, PRUNE_PLAYBOOK_NAME, COUCH_SHARD_PLAN
from commcare_cloud.commands.migrations.couchdb import generate_rsync_lists, \
    generate_shard_prune_playbook, generate_shard_plan, get_migration_file_configs
from commcare_cloud.commands.migrations.copy_files import get_file_list_filename
from commcare_cloud.environment.main import get_environment
from tests.test_utils import get_file_contents

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'couch_migration_config')
PLANS_DIR = os.path.join(TEST_ENVIRONMENTS_DIR, 'plans')
TEST_PLANS = os.listdir(PLANS_DIR)

def tearDown():
    # delete generated files
    for plan_name in TEST_PLANS:
        migration = _get_migration(plan_name)
        shutil.rmtree(migration.rsync_files_path)


def get_shard_allocation_func(mock_shard_allocation):
    allocations_by_db = {
        allocation['_id']: ShardAllocationDoc.wrap(allocation)
        for allocation in mock_shard_allocation
    }

    def _mock_get_shard_allocation(config, db_name, create=False):
        return allocations_by_db[db_name]

    return _mock_get_shard_allocation


@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_couch_config(plan_name):
    migration = _get_migration(plan_name)
    assert not migration.separate_source_and_target

    expected_couch_config_json = _get_expected_yml(plan_name, 'expected_couch_config.yml')
    assert expected_couch_config_json == migration.target_couch_config.to_json(), migration.target_couch_config.to_json()


@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_get_migration_file_configs(plan_name):
    migration = _get_migration(plan_name)

    migration_file_configs = _generate_plan_and_rsync_lists(migration, plan_name)

    for target_host, migration_configs in migration_file_configs.items():
        for config in migration_configs:
            file_name = get_file_list_filename(config)

            actual = get_file_contents(os.path.join(migration.rsync_files_path, target_host, file_name))
            expected = _get_test_file(plan_name, 'expected_{}'.format(file_name))
            assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)


@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_generated_plan(plan_name):
    migration = _get_migration(plan_name)
    _generate_plan_and_rsync_lists(migration, plan_name)

    actual = _get_yml(migration.shard_plan_path)
    expected = _get_expected_yml(plan_name, 'expected_{}'.format(COUCH_SHARD_PLAN))
    assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)


@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_generate_shard_prune_playbook(plan_name):
    migration = _get_migration(plan_name)
    mock_shard_allocation = _get_expected_yml(plan_name, 'mock_shard_allocation_post_migration.yml')
    mock_func = get_shard_allocation_func(mock_shard_allocation)
    with patch('commcare_cloud.commands.migrations.couchdb.get_shard_allocation', mock_func),\
            patch('commcare_cloud.commands.migrations.couchdb.get_db_list', return_value=['commcarehq', 'commcarehq__apps']):
        nodes = generate_shard_prune_playbook(migration)

    if nodes:
        actual = _get_yml(migration.prune_playbook_path)
        expected = _get_expected_yml(plan_name, 'expected_{}'.format(PRUNE_PLAYBOOK_NAME))
        assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)
    else:
        assert not os.path.exists(migration.prune_playbook_path), migration.prune_playbook_path


def _generate_plan_and_rsync_lists(migration, plan_name):
    mock_shard_allocation = _get_expected_yml(plan_name, 'mock_shard_allocation_pre_migration.yml')
    mock_func = get_shard_allocation_func(mock_shard_allocation)

    db_info = [
        (allocation['_id'], 10, {'a': 10}, sorted(allocation['by_range']), ShardAllocationDoc.wrap(allocation))
        for allocation in mock_shard_allocation
    ]
    with patch('couchdb_cluster_admin.suggest_shard_allocation.get_db_info', return_value=db_info):
        generate_shard_plan(migration)

    with patch('couchdb_cluster_admin.file_plan.get_shard_allocation', mock_func):
        # this also get's called in generate_rsync_lists but we want the result to test against
        migration_file_configs = get_migration_file_configs(migration)
        generate_rsync_lists(migration)
    return migration_file_configs


def _get_migration(plan_name):
    plan_path = os.path.join(PLANS_DIR, plan_name, 'plan.yml')
    migration = CouchMigration(get_environment('env1'), plan_path)
    return migration


def _get_expected_yml(plan_name, filename):
    return _get_yml(os.path.join(PLANS_DIR, plan_name, filename))


def _get_yml(path):
    with open(path, 'r') as exp:
        return yaml.load(exp)


def _get_test_file(plan_name, filename):
    return get_file_contents(os.path.join(PLANS_DIR, plan_name, filename))


