from types import SimpleNamespace
from unittest.mock import patch

import pytest
from couchdb_cluster_admin.doc_models import ShardAllocationDoc

from commcare_cloud.commands.command_base import CommandError
from commcare_cloud.commands.migrations.couchdb_shard_map import (
    ResetCouchdbShardMap,
    single_node_allocation,
)

OLD_IPS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
OLD_NODES = [f'couchdb@{ip}' for ip in OLD_IPS]
NEW_IP = '10.9.9.9'
NEW_NODE = f'couchdb@{NEW_IP}'
RANGES = ['00000000-7fffffff', '80000000-ffffffff']


def _prod_doc(db_name='commcarehq'):
    return ShardAllocationDoc.wrap({
        '_id': db_name,
        '_rev': '3-abc',
        'shard_suffix': [46, 49, 50, 51],  # char codes for ".123"
        'changelog': [['add', r, n] for r in RANGES for n in OLD_NODES],
        'by_node': {n: list(RANGES) for n in OLD_NODES},
        'by_range': {r: list(OLD_NODES) for r in RANGES},
    })


def test_all_ranges_move_to_new_node():
    new_doc = single_node_allocation(_prod_doc(), NEW_NODE)
    assert new_doc.by_range == {r: [NEW_NODE] for r in RANGES}
    assert new_doc.by_node == {NEW_NODE: RANGES}


def test_identity_fields_are_kept():
    new_doc = single_node_allocation(_prod_doc(), NEW_NODE)
    assert new_doc._id == 'commcarehq'
    assert new_doc._rev == '3-abc'
    assert new_doc.usable_shard_suffix == '.123'


def test_changelog_is_dropped():
    new_doc = single_node_allocation(_prod_doc(), NEW_NODE)
    assert new_doc.changelog == []


MODULE = 'commcare_cloud.commands.migrations.couchdb_shard_map'


def _run_command(couch_hosts):
    """Run the command against a fake couch holding two prod-style maps.

    Returns the docs that were written.
    """
    docs = {name: _prod_doc(name) for name in ['commcarehq', 'commcarehq__users']}
    written = []
    with patch(f'{MODULE}.get_environment') as get_environment, \
            patch(f'{MODULE}.get_couch_config'), \
            patch(f'{MODULE}.get_db_list', return_value=list(docs)), \
            patch(f'{MODULE}.get_shard_allocation', side_effect=lambda _, name: docs[name]), \
            patch(f'{MODULE}.put_shard_allocation', side_effect=lambda _, doc: written.append(doc)), \
            patch('commcare_cloud.commands.ansible.helpers.ask', return_value=True):
        get_environment.return_value.groups = {'couchdb2': couch_hosts}
        args = SimpleNamespace(env_name='backup-production', skip_check=False)
        ResetCouchdbShardMap(parser=None).run(args, [])
    return written


def test_command_writes_single_node_map_for_every_db():
    written = _run_command([NEW_IP])
    assert [doc.db_name for doc in written] == ['commcarehq', 'commcarehq__users']
    for doc in written:
        assert doc.by_node == {NEW_NODE: RANGES}


def test_command_refuses_multiple_couch_hosts():
    with pytest.raises(CommandError, match='3 couchdb2 hosts'):
        _run_command(OLD_IPS)
