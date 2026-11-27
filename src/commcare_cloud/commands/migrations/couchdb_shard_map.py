from clint.textui import puts
from couchdb_cluster_admin.doc_models import ShardAllocationDoc
from couchdb_cluster_admin.utils import (
    get_db_list,
    get_shard_allocation,
    put_shard_allocation,
)

from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import run_action_with_check_mode
from commcare_cloud.commands.ansible.ops_tool import get_couch_config
from commcare_cloud.commands.command_base import CommandBase, CommandError
from commcare_cloud.environment.main import get_environment


class ResetCouchdbShardMap(CommandBase):
    command = 'reset-couchdb-shard-map'
    help = """
    Point every CouchDB database's shard map at the environment's only couch node.

    For a single node restored from a volume of a multi-node cluster, where
    the shard maps still name the old nodes (BCP "Prepare Couch Cluster").
    Refuses to run if the environment has more than one couchdb2 host.
    """
    arguments = (shared_args.SKIP_CHECK_ARG,)

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        couch_hosts = environment.groups['couchdb2']
        if len(couch_hosts) != 1:
            raise CommandError(
                "{} has {} couchdb2 hosts; this command only supports one.".format(
                    args.env_name, len(couch_hosts)))

        couch_config = get_couch_config(environment)
        node = 'couchdb@{}'.format(couch_hosts[0])
        changes = []
        for db_name in get_db_list(couch_config.get_control_node()):
            current_doc = get_shard_allocation(couch_config, db_name)
            changes.append((current_doc, single_node_allocation(current_doc, node)))

        def run_check():
            for current_doc, new_doc in changes:
                puts('{}: {} -> {}'.format(
                    current_doc.db_name,
                    ', '.join(sorted(current_doc.by_node)),
                    ', '.join(sorted(new_doc.by_node)),
                ))
            return 0

        def run_apply():
            for _, new_doc in changes:
                put_shard_allocation(couch_config, new_doc)
                puts('{}: updated'.format(new_doc.db_name))
            return 0

        return run_action_with_check_mode(run_check, run_apply, args.skip_check)


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
