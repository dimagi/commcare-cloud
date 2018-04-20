from commcare_cloud.commands.inventory_lookup.inventory_lookup import DjangoManage
from commcare_cloud.environment.main import get_environment


class DumpData(DjangoManage):
    """
    Single place to support taking data dumps for a domain from various databases.
    It's recommended to always run this in a tmux session by passing the option --tmux because
    the dumping process can take quite long for domains with large amounts of data
    commcare-cloud softlayer dump-data enikshay all --tmux
    You can also run things in parallel by running commands with different options like
    1. commcare-cloud softlayer dump-data enikshay sql --tmux
    2. commcare-cloud softlayer dump-data enikshay couch --tmux
    3. commcare-cloud softlayer dump-data enikshay riak --tmux
    or even break this down further by doing
    1. commcare-cloud softlayer dump-data enikshay couch --dumper domain --dumper toggles --tmux
    2. commcare-cloud softlayer dump-data enikshay couch --dumper couch --tmux
    3. commcare-cloud softlayer dump-data enikshay riak --exporter applications --tmux
    4. commcare-cloud softlayer dump-data enikshay riak --exporter saved_exports --exporter multimedia --tmux
    5. commcare-cloud softlayer dump-data enikshay riak --exporter sql_xforms --limit_to_db p1 --tmux
    """
    command = 'dump-data'
    help = (
        "Dump data for a domain in different databases"
    )
    COUCH_DATA_DUMPERS = ['domain', 'couch', 'toggles']
    SQL_DATA_DUMPERS = ['sql']
    DATA_DUMPERS = COUCH_DATA_DUMPERS + SQL_DATA_DUMPERS
    EXPORTERS = ['applications', 'multimedia', 'couch_xforms',
                 'sql_xforms', 'saved_exports', 'demo_user_restores']

    def make_parser(self):
        super(DumpData, self).make_parser()
        self.parser.add_argument(
            'domain'
        )
        self.parser.add_argument(
            'db',
            choices=['all', 'pg', 'couch', 'riak']
        )
        self.parser.add_argument(
            '--dumper',
            action='append',
            choices=self.DATA_DUMPERS,
            help="dumper to be used for couch db data dumps. Skip for all."
        )
        self.parser.add_argument(
            '--exporter',
            action='append',
            choices=self.EXPORTERS,
            help="exporter to be used for riak db data dumps. Skip for all."
        )
        self.parser.add_argument(
            '--limit_to_db',
            help="Used to riak imports to fetch data for a particualr db partition only like in case of sql_xforms"
                 "which would be present in different shards."
                 "This would help in running things in parallel for larger domains"
        )

    def get_manage_args_for_pg(self, args):
        manage_args = ['dump_domain_data', args.domain]
        if args.dumper:
            for dumper in args.dumper:
                assert dumper in self.SQL_DATA_DUMPERS, "Supported Dumpers for pg: {dumpers}".format(
                    dumpers=','.join(self.SQL_DATA_DUMPERS)
                )
                manage_args.extend(['--dumper', dumper])
        else:
            for dumper in self.SQL_DATA_DUMPERS:
                manage_args.extend(['--dumper', dumper])
        return manage_args

    def get_manage_args_for_couch(self, args):
        manage_args = ['dump_domain_data', args.domain]
        if args.dumper:
            for dumper in args.dumper:
                assert dumper in self.COUCH_DATA_DUMPERS, "Supported Dumpers for couch: {dumpers}".format(
                    dumpers=','.join(self.COUCH_DATA_DUMPERS)
                )
                manage_args.extend(['--dumper', dumper])
        else:
            for dumper in self.COUCH_DATA_DUMPERS:
                manage_args.extend(['--dumper', dumper])
        return manage_args

    def get_manage_args_for_riak(self, args):
        manage_args = ['run_blob_export', args.domain]
        if args.exporter:
            for exporter in args.exporter:
                assert exporter in self.EXPORTERS, "Supported Exporters for riak: {exporters}".format(
                    exporters=','.join(self.EXPORTERS)
                )
                manage_args.extend(['--exporter', exporter])
        else:
            manage_args.extend(['--all'])
        return manage_args

    def run(self, args, manage_args):
        assert bool(manage_args) is False, \
            "Arguments for management command not supported." \
            "Run django-manage to run any specific management command"
        if args.db == 'pg':
            manage_args = self.get_manage_args_for_pg(args)
        elif args.db == 'couch':
            manage_args = self.get_manage_args_for_couch(args)
        elif args.db == 'riak':
            manage_args = self.get_manage_args_for_riak(args)
        elif args.db == 'all':
            manage_args = ['dump_all_domain_data', args.domain]
        if args.limit_to_db:
            environment = get_environment(args.env_name)
            partitions = environment.postgresql_config.dbs.form_processing.partitions.keys()
            assert args.limit_to_db in partitions, "Available paritions {partitions}".format(
                partitions=','.join(partitions))
            manage_args.extend(['--limit_to_db', args.limit_to_db])
        super(DumpData, self).run(args, manage_args)
