from __future__ import print_function

import os
import shutil

import yaml
from couchdb_cluster_admin.doc_models import ShardAllocationDoc
from mock.mock import patch
from nose_parameterized import parameterized

from commcare_cloud.commands.migrations.config import CouchMigration, PRUNE_PLAYBOOK_NAME, COUCH_SHARD_PLAN
from commcare_cloud.commands.migrations.couchdb import generate_rsync_lists, \
    COUCHDB_RSYNC_SCRIPT, clean, generate_shard_prune_playbook, plan, generate_shard_plan
from commcare_cloud.environment.main import get_environment

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'migration_config')
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
def test_generate_rsync_lists(plan_name):
    migration = _get_migration(plan_name)
    assert not migration.separate_source_and_target
    with open(os.path.join(PLANS_DIR, plan_name, 'expected_couch_config.yml')) as f:
        expected_couch_config_json = yaml.load(f)

    assert expected_couch_config_json == migration.target_couch_config.to_json(), migration.target_couch_config.to_json()

    files_by_host = _generate_plan_and_rsync_lists(migration, plan_name)

    with open(os.path.join(PLANS_DIR, plan_name, 'expected_{}'.format(COUCHDB_RSYNC_SCRIPT))) as exp:
        expected_script = exp.read()

    for host, file_paths in files_by_host.items():
        for file_path in file_paths:
            file_name = file_path.split('/')[-1]
            with open(file_path, 'r') as f:
                actual = f.read()

            with open(os.path.join(PLANS_DIR, plan_name, 'expected_{}'.format(file_name))) as exp:
                expected = exp.read()
            assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)

        script_path = os.path.join(migration.rsync_files_path, host, COUCHDB_RSYNC_SCRIPT)
        with open(script_path, 'r') as exp:
            script_source = exp.read()

        assert expected_script == script_source, "'{}'".format(script_source)



@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_generate_rsync_lists(plan_name):
    migration = _get_migration(plan_name)
    _generate_plan_and_rsync_lists(migration, plan_name)

    with open(migration.shard_plan_path, 'r') as f:
        actual = yaml.load(f)
    with open(os.path.join(PLANS_DIR, plan_name, 'expected_{}'.format(COUCH_SHARD_PLAN))) as exp:
        expected = yaml.load(exp)
        assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)


@parameterized(TEST_PLANS)
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENVIRONMENTS_DIR)
def test_generate_shard_prune_playbook(plan_name):
    migration = _get_migration(plan_name)
    with open(os.path.join(PLANS_DIR, plan_name, 'mock_shard_allocation.yml')) as f:
        mock_shard_allocation = yaml.load(f)
    mock_func = get_shard_allocation_func(mock_shard_allocation)
    with patch('couchdb_cluster_admin.file_plan.get_shard_allocation', mock_func):
        nodes = generate_shard_prune_playbook(migration)

    if nodes:
        with open(migration.prune_playbook_path, 'r') as f:
            actual = yaml.load(f)
        with open(os.path.join(PLANS_DIR, plan_name, 'expected_{}'.format(PRUNE_PLAYBOOK_NAME))) as exp:
            expected = yaml.load(exp)
            assert expected == actual, "file lists mismatch:\n\nExpected\n{}\nActual\n{}".format(expected, actual)
    else:
        assert not os.path.exists(migration.prune_playbook_path), migration.prune_playbook_path


def _generate_plan_and_rsync_lists(migration, plan_name):
    with open(os.path.join(PLANS_DIR, plan_name, 'mock_shard_allocation.yml')) as f:
        mock_shard_allocation = yaml.load(f)
    mock_func = get_shard_allocation_func(mock_shard_allocation)

    db_info = [
        (allocation['_id'], 10, {'a': 10}, sorted(allocation['by_range']), ShardAllocationDoc.wrap(allocation))
        for allocation in mock_shard_allocation
    ]
    with patch('couchdb_cluster_admin.suggest_shard_allocation.get_db_info', return_value=db_info):
        generate_shard_plan(migration)

    with patch('couchdb_cluster_admin.file_plan.get_shard_allocation', mock_func):
        files_by_host = generate_rsync_lists(migration)
    return files_by_host


def _get_migration(plan_name):
    plan_path = os.path.join(PLANS_DIR, plan_name, 'plan.yml')
    migration = CouchMigration(get_environment('env1'), plan_path)
    return migration
