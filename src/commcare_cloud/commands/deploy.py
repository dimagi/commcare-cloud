from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch, ask
from commcare_cloud.colors import color_notice, color_summary
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment


class Deploy(CommandBase):
    command = 'deploy'
    help = (
        "Deploy CommCare"
    )

    arguments = (
        Argument('component', nargs='?', choices=['commcare', 'formplayer'], default='commcare', help="""
            The component to deploy.
        """),
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
        commcare_branch = self._confirm_commcare_branch(environment, args.commcare_branch,
                                                        quiet=args.quiet)
        if args.component == 'commcare':
            print(color_summary("You are about to deploy commcare"))
            print(color_summary("branch: {}".format(commcare_branch)))
            if ask('Deploy commcare?', quiet=args.quiet):
                print(color_notice("Formplayer will not be deployed right now,"))
                print(color_notice("but we recommend deploying formplayer about once a month as well."))
                print(color_notice("It causes about 1 minute of service interruption to Web Apps and App Preview,"))
                print(color_notice("but keeps these services up to date."))
                print(color_notice("You can do so by running `commcare-cloud <env> deploy formplayer`"))

                self.deploy_commcare(environment, commcare_branch, args, unknown_args)
        elif args.component == 'formplayer':
            self.deploy_formplayer(environment, commcare_branch, args, unknown_args)

    def deploy_commcare(self, environment, commcare_branch, args, unknown_args):
        fab_func_args = self.get_deploy_commcare_fab_func_args(args)
        commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                       '--set', 'code_branch={}'.format(commcare_branch),
                       branch=args.branch, *unknown_args)

    def deploy_formplayer(self, environment, commcare_branch, args, unknown_args):
        """
        Because of how our fab code is structured, the code_branch variable is still required,
        even though it is used only barely, if in any consequential way at all.
        """
        commcare_cloud(environment.name, 'fab', 'deploy_formplayer',
                       '--set', 'code_branch={}'.format(commcare_branch),
                       branch=args.branch, *unknown_args)

    @staticmethod
    def get_deploy_commcare_fab_func_args(args):
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
    def _confirm_commcare_branch(environment, commcare_branch, quiet):
        default_branch = environment.fab_settings_config.default_branch
        if not commcare_branch:
            return default_branch

        if commcare_branch != default_branch:
            branch_message = (
                "Whoa there bud! You're using branch {commcare_branch}. "
                "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
            ).format(commcare_branch=commcare_branch)
            if not ask(branch_message, quiet=quiet):
                exit(-1)

        return commcare_branch
