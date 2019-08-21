from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment


class Deploy(CommandBase):
    command = 'deploy'
    help = (
        "Deploy CommCare"
    )

    arguments = (
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        commcare_cloud(environment.name, 'fab', 'deploy', branch=args.branch, *unknown_args)
