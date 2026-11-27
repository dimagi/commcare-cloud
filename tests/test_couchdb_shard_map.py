from couchdb_cluster_admin.doc_models import ShardAllocationDoc

from commcare_cloud.commands.migrations.couchdb_shard_map import single_node_allocation

OLD_IPS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
OLD_NODES = [f'couchdb@{ip}' for ip in OLD_IPS]
NEW_IP = '10.9.9.9'
NEW_NODE = f'couchdb@{NEW_IP}'
RANGES = ['00000000-7fffffff', '80000000-ffffffff']


def _prod_doc():
    return ShardAllocationDoc.wrap({
        '_id': 'commcarehq',
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

