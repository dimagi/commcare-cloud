from commcare_cloud.commands.inventory_lookup.inventory_lookup import DjangoManage


class DumpData(DjangoManage):
    """
    It's recommended to always run this in a tmux session by passing the option --tmux because
    the dumping process can take quite long for domains with large amounts of data
    commcare-cloud softlayer dump-domain-data enikshay --tmux
    Look at the management command for more examples
    """
    command = 'dump-domain-data'
    help = (
        "Dump data for a domain in different databases."
        "The resultant files are stored on the server where it's run. Check django-manage "
        "for more options"
    )

    def make_parser(self):
        super(DumpData, self).make_parser()
        self.parser.add_argument(
            'domain'
        )

    def run(self, args, manage_args):
        new_manage_args = ['dump_domain_data', args.domain]
        new_manage_args.extend(manage_args)
        super(DumpData, self).run(args, new_manage_args)
