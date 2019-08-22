from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment


class Deploy(CommandBase):
    command = 'deploy'
    help = (
        "Deploy CommCare"
    )

    arguments = (
        Argument('--resume', action='store_true', help="""
            Rather than starting a new deploy, start where you left off the last one.
        """),
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        if args.resume:
            fab_func_args = ':resume=yes'
        else:
            fab_func_args = ''
        commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                       branch=args.branch, *unknown_args)
