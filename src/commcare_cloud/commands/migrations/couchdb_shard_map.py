from couchdb_cluster_admin.doc_models import ShardAllocationDoc


def single_node_allocation(doc, node):
    """Return a copy of ``doc`` with every shard range allocated to ``node``.

    The changelog is dropped, matching the manual "Prepare Couch Cluster"
    runbook step this replaces.
    """
    new_doc = ShardAllocationDoc(
        _id=doc._id,
        _rev=doc._rev,
        shard_suffix=doc.shard_suffix,
        props=doc.props,
    )
    new_doc.populate_from_range({shard: [node] for shard in doc.by_range})
    return new_doc
