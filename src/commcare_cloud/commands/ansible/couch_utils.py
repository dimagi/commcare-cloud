import itertools
from collections import defaultdict
from operator import attrgetter
from six.moves import urllib_parse

import jsonobject
from couchdb_cluster_admin.utils import do_node_local_request, get_membership, NodeDetails


def get_cluster_shard_details(config):
    nodes = get_nodes(config)
    return list(itertools.chain.from_iterable(get_node_shard_details(node_details) for node_details in nodes))


def get_node_shard_details(node_details):
    shards = get_node_shards(node_details)
    return [get_shard_details(node_details, shard) for shard in shards]


def get_node_shards(node_details):
    return [
        local_db for local_db in do_node_local_request(node_details, "_all_dbs")
        if local_db.startswith("shards")
    ]


def get_shard_details(node_details, shard_name):
    data = do_node_local_request(node_details, urllib_parse.quote(shard_name, safe=""))
    data["node"] = "couchdb@{}".format(node_details.ip)
    data["shard_name"] = data["db_name"]
    data["db_name"] = shard_name.split("/")[-1].split(".")[0]
    return ShardDetails(data)


def get_nodes(config):
    config.get_control_node()
    node_details = []
    for member in get_membership(config).cluster_nodes:
        address = member.split('@')[1]
        node_details.append(NodeDetails(
            address,
            config.control_node_port,
            config.control_node_local_port,
            config.username,
            config._password,
            None
        ))
    return node_details


def print_shard_table(shard_allocation_docs, shard_details):
    last_header = None
    db_names = [shard_allocation_doc.db_name for shard_allocation_doc in shard_allocation_docs]
    max_db_name_len = max(list(map(len, db_names)))

    shard_details = sorted(shard_details, key=attrgetter('db_name'))
    shards_by_db = {
        group: list(shards)
        for group, shards in itertools.groupby(shard_details, key=attrgetter('db_name'))
    }

    for shard_allocation_doc in shard_allocation_docs:
        if not shard_allocation_doc.validate_allocation():
            print("error")
            continue

        db_shard_details = shards_by_db[shard_allocation_doc.db_name]
        this_header = sorted(shard_allocation_doc.by_range)
        print(get_printable(
            shard_allocation_doc,
            db_shard_details,
            include_shard_names=(last_header != this_header),
            db_name_len=max_db_name_len
        ))
        last_header = this_header


def get_printable(shard_doc, shard_details, include_shard_names, db_name_len=20):
    parts = []
    first_column = u'{{: <{}}}  '.format(db_name_len)
    other_columns = u'{: ^20s}  '
    if include_shard_names:
        parts.append(first_column.format(u''))
        for shard in sorted(shard_doc.by_range):
            parts.append(other_columns.format(shard))
        parts.append(u'\n')
    parts.append(first_column.format(shard_doc.db_name))
    for shard, nodes in sorted(shard_doc.by_range.items()):
        parts.append(other_columns.format(u','.join(map(shard_doc.config.format_node_name, nodes))))
    parts.append(u'\n')

    shards_by_shard_name = defaultdict(list)
    for shard_detail in shard_details:
        shards_by_shard_name[shard_detail.shard_name_short].append(shard_detail)

    for shard_name, nodes in sorted(shard_doc.by_range.items()):
        shards = {shard.node: shard for shard in shards_by_shard_name[shard_name]}
        doc_counts = {
            "doc_count": None,
            "doc_del_count": None
        }
        for node in nodes:
            shard = shards[node]
            if doc_counts["doc_count"] is None:
                doc_counts["doc_count"] = [shard.doc_count]
                doc_counts["doc_del_count"] = [shard.doc_del_count]
            else:
                first_doc_count, first_doc_del_count = doc_counts["doc_count"][0], doc_counts["doc_del_count"][0]
                doc_counts["doc_count"].append(shard.doc_count - first_doc_count)
                doc_counts["doc_del_count"].append(shard.doc_del_count - first_doc_del_count)
        parts.append(other_columns.format(u','.join(['{0:+}'.format(c) for c in doc_counts["doc_count"]])))
        parts.append(u'\n')
        parts.append(other_columns.format(u','.join(['{0:+}'.format(c) for c in doc_counts["doc_del_count"]])))

    return ''.join(parts)


class ShardDetails(jsonobject.JsonObject):
    node = jsonobject.StringProperty()
    db_name = jsonobject.StringProperty()

    # shards/c0000000-dfffffff/commcarehq.1541009837
    shard_name = jsonobject.StringProperty()
    engine = jsonobject.StringProperty()
    doc_count = jsonobject.IntegerProperty()
    doc_del_count = jsonobject.IntegerProperty()
    purge_seq = jsonobject.IntegerProperty()
    compact_running = jsonobject.BooleanProperty()
    sizes = jsonobject.DictProperty()
    disk_size = jsonobject.IntegerProperty()
    data_size = jsonobject.IntegerProperty()
    other = jsonobject.DictProperty()
    instance_start_time = jsonobject.StringProperty()
    disk_format_version = jsonobject.IntegerProperty()
    committed_update_seq = jsonobject.IntegerProperty()
    compacted_seq = jsonobject.IntegerProperty()
    uuid = jsonobject.StringProperty()

    @property
    def shard_name_short(self):
        return self.shard_name.split('/')[1]
