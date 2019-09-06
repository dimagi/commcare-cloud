from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch, ask
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
        Argument('--skip-record', action='store_true', help="""
            Skip the steps involved in recording and announcing the fact of the deploy.
        """),
        Argument('--commcare-branch', help="""
            The name of the commcare-hq git branch to deploy. 
        """, default=None),
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        commcare_branch = self._confirm_commcare_branch(environment, args.commcare_branch)
        fab_func_args = self.get_fab_func_args(args)
        commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                       '--set', 'code_branch={}'.format(commcare_branch),
                       branch=args.branch, *unknown_args)

    @staticmethod
    def get_fab_func_args(args):
        fab_func_args = []

        if args.quiet:
            fab_func_args.append('confirm=no')
        if args.resume:
            fab_func_args.append('resume=yes')
        if args.skip_record:
            fab_func_args.append('skip_record=yes')

        if fab_func_args:
            return ':{}'.format(','.join(fab_func_args))
        else:
            return ''

    @staticmethod
    def _confirm_commcare_branch(environment, commcare_branch):
        default_branch = environment.fab_settings_config.default_branch
        if not commcare_branch:
            print("commcare_branch not specified, using '{}'. "
                  "You can override this with '--commcare-branch=<branch>'"
                  .format(default_branch))
            return default_branch

        if commcare_branch != default_branch:
            branch_message = (
                "Whoa there bud! You're using branch {commcare_branch}. "
                "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
            ).format(commcare_branch=commcare_branch)
            if not ask(branch_message):
                exit(-1)

        return commcare_branch
