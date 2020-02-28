from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch, ask
from commcare_cloud.colors import color_notice, color_summary
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible import ansible_playbook
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.terraform.aws import get_default_username
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
            The name of the commcare-hq git branch to deploy. Mutually exclusive with commcare-hash.
        """, default=None),
        Argument('--commcare-hash', help="""
            The hash of a commcare-hq commit to deploy. Mutually exclusive with commcare-branch.
        """, default=None),
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        if args.commcare_branch and args.commcare_hash:
            print(color_notice("You cannot deploy from both a commcare-branch and a commcare-hash."))
            exit(-1)
        commcare_commit = args.commcare_branch or args.commcare_hash
        self._confirm_commcare_commit(environment, commcare_commit, quiet=args.quiet)
        if args.component == 'commcare':
            print(color_summary("You are about to deploy commcare from {}".format(commcare_commit)))
            if ask('Deploy commcare?', quiet=args.quiet):
                print(color_notice("Formplayer will not be deployed right now,"))
                print(color_notice("but we recommend deploying formplayer about once a month as well."))
                print(color_notice("It causes about 1 minute of service interruption to Web Apps and App Preview,"))
                print(color_notice("but keeps these services up to date."))
                print(color_notice("You can do so by running `commcare-cloud <env> deploy formplayer`"))
                self.deploy_commcare(environment, commcare_commit, args, unknown_args)
        elif args.component == 'formplayer':
            self._announce_formplayer_deploy_start(environment)
            self.deploy_formplayer(environment, args, unknown_args)

    def deploy_commcare(self, environment, commcare_commit, args, unknown_args):
        fab_func_args = self.get_deploy_commcare_fab_func_args(args)
        commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                       '--set', 'code_branch={}'.format(commcare_commit),
                       branch=args.branch, *unknown_args)

    def deploy_formplayer(self, environment, args, unknown_args):
        def run_ansible_playbook_command():
            skip_check = True
            environment.create_generated_yml()
            ansible_context = AnsibleContext(args)
            return ansible_playbook.run_ansible_playbook(
                environment, 'deploy_stack.yml', ansible_context,
                skip_check=skip_check, quiet=skip_check, always_skip_check=skip_check, limit='formplayer',
                use_factory_auth=False, unknown_args=('--tags=formplayer_deploy',),
                respect_ansible_skip=True,
            )
        rc = run_ansible_playbook_command()
        if rc != 0:
            return rc
        rc = commcare_cloud(
            args.env_name, 'run-shell-command', 'formplayer',
            ('supervisorctl reread; '
             'supervisorctl update {project}-{deploy_env}-formsplayer-spring; '
             'supervisorctl restart {project}-{deploy_env}-formsplayer-spring').format(
                project='commcare-hq',
                deploy_env=environment.meta_config.deploy_env,
            ), '-b',
        )
        if rc != 0:
            return rc

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
    def _confirm_commcare_commit(environment, commcare_commit, quiet=False):
        default_branch = environment.fab_settings_config.default_branch
        if not commcare_commit:
            return default_branch

        if commcare_commit != default_branch:
            message = (
                "Whoa there bud! You're deploying from {commcare_commit}. "
                "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
            ).format(commcare_commit=commcare_commit)
            if not ask(message, quiet=quiet):
                exit(-1)

    @staticmethod
    def _announce_formplayer_deploy_start(environment):
        mail_admins(
            environment,
            subject="{user} has initiated a formplayer deploy to {environment}.".format(
                user=get_default_username(),
                environment=environment.meta_config.deploy_env,
            ),
            message='',
        )


def mail_admins(environment, subject, message):
    if environment.fab_settings_config.email_enabled:
        commcare_cloud(
            environment.name, 'django-manage', 'mail_admins',
            '--subject', subject,
            message,
            '--environment', environment.meta_config.deploy_env
        )
