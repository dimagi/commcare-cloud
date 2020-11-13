import itertools
from collections import defaultdict
from operator import attrgetter
from six.moves import urllib_parse

import jsonobject
from couchdb_cluster_admin.utils import do_node_local_request, get_membership, NodeDetails
from tabulate import tabulate


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
    shard_details = sorted(shard_details, key=attrgetter('db_name'))
    shards_by_db = {
        group: list(shards)
        for group, shards in itertools.groupby(shard_details, key=attrgetter('db_name'))
    }

    tables = defaultdict(list)
    for shard_allocation_doc in shard_allocation_docs:
        if not shard_allocation_doc.validate_allocation():
            print(u"In this allocation by_node and by_range are inconsistent:", repr(shard_allocation_doc))
            continue

        db_shard_details = shards_by_db.get(shard_allocation_doc.db_name)
        this_header = tuple(sorted(shard_allocation_doc.by_range))
        table = tables[this_header]
        table.extend(get_shard_table_rows(
            shard_allocation_doc,
            db_shard_details,
        ))
    for header, rows in tables.items():
        print(tabulate(rows, header))


def get_shard_table_rows(shard_doc, shard_details):
    rows, shard_row = [], []
    shard_row.append(shard_doc.db_name)
    for shard, nodes in sorted(shard_doc.by_range.items()):
        shard_row.append(u','.join(map(shard_doc.config.format_node_name, nodes)))
    rows.append(shard_row)

    if shard_details:
        doc_count_row = ["...doc_count"]
        doc_del_count_row = ["...doc_del_count"]
        shards_by_shard_name = defaultdict(list)
        for shard_detail in shard_details:
            shards_by_shard_name[shard_detail.shard_name_short].append(shard_detail)

        def format_counts(counts):
            return u','.join([
                str(cnt) if i == 0 else '{0:+}'.format(cnt)
                for i, cnt in enumerate(counts)
            ])

        for shard_name, nodes in sorted(shard_doc.by_range.items()):
            shards = {shard.node: shard for shard in shards_by_shard_name[shard_name]}
            doc_count, doc_del_count = None, None
            for node in nodes:
                shard = shards[node]
                if doc_count is None:
                    doc_count = [shard.doc_count]
                    doc_del_count = [shard.doc_del_count]
                else:
                    doc_count.append(shard.doc_count - doc_count[0])
                    doc_del_count.append(shard.doc_del_count - doc_del_count[0])

            doc_count_row.append(format_counts(doc_count))
            doc_del_count_row.append(format_counts(doc_del_count))
        rows.append(doc_count_row)
        rows.append(doc_del_count_row)
        rows.append([])
    return rows


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
