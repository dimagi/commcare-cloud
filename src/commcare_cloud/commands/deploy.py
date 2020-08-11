import sys
from textwrap import dedent

from clint.textui import indent

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask, check_branch
from commcare_cloud.colors import color_notice, color_summary, color_warning
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible import ansible_playbook
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.commands.terraform.aws import get_default_username
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs


class Deploy(CommandBase):
    command = 'deploy'
    help = (
        "Deploy CommCare"
    )

    arguments = (
        Argument('component', nargs='?', choices=['commcare', 'formplayer'], help="""
            The component to deploy. If not specified, will deploy CommCare, or
            both, if always_deploy_formplayer is set in meta.yml
        """),
        Argument('--resume', action='store_true', help="""
            Rather than starting a new deploy, start where you left off the last one.
        """),
        Argument('--skip-record', action='store_true', help="""
            Skip the steps involved in recording and announcing the fact of the deploy.
        """),
        Argument('--commcare-rev', help="""
            The name of the commcare-hq git branch, tag, or SHA-1 commit hash to deploy.
        """, default=None),
        Argument('--set', dest='fab_settings', help="""
            fab settings in k1=v1,k2=v2 format to be passed down to fab 
        """, default=None),
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
    )

    def modify_parser(self):
        env_name = sys.argv[1]
        if env_name not in get_available_envs():
            return

        environment = get_environment(env_name)
        if environment.meta_config.git_repositories:
            for repo in environment.meta_config.git_repositories:
                Argument('--{}-rev'.format(repo.name), help="""
                    The name of the git branch, tag, or SHA-1 commit hash to deploy for the
                    '{}' ({}) repository
                """.format(repo.name, repo.url)).add_to_parser(self.parser)

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        deploy_revs = self._confirm_deploy_revs(environment, args, quiet=args.quiet)

        deploy_component = args.component
        if deploy_component == None:
            deploy_component = 'both' if environment.meta_config.always_deploy_formplayer else 'commcare'

        if deploy_component in ['commcare', 'both']:
            print(color_summary("You are about to deploy the following code:"))
            with indent():
                for name, rev in deploy_revs:
                    print(color_summary("{}: {}".format(name, rev)))
            if ask('Continue with deploy?', quiet=args.quiet):
                if deploy_component != 'both':
                    _warn_no_formplayer()
                self.deploy_commcare(environment, deploy_revs, args, unknown_args)
        if deploy_component in ['formplayer', 'both']:
            if deploy_component != 'both':
                if args.commcare_rev:
                    print(color_warning('--commcare-rev does not apply to a formplayer deploy and will be ignored'))
                if args.fab_settings:
                    print(color_warning('--set does not apply to a formplayer deploy and will be ignored'))
            self._announce_formplayer_deploy_start(environment)
            self.deploy_formplayer(environment, args, unknown_args)

    def deploy_commcare(self, environment, deploy_revs, args, unknown_args):
        fab_func_args = self.get_deploy_commcare_fab_func_args(args)
        fab_settings = [args.fab_settings] if args.fab_settings else []
        for name, rev in deploy_revs:
            var = 'code_branch' if name == 'commcare' else '{}_code_branch'.format(name)
            fab_settings.append('{}={}'.format(var, rev))
        commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                       '--set', ','.join(fab_settings),
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
    def _confirm_deploy_revs(environment, args, quiet=False):
        default_branch = environment.fab_settings_config.default_branch
        branches = [
            ('commcare', 'commcare_rev', default_branch),
        ]
        for repo in environment.meta_config.git_repositories:
            branches.append((repo.name, '{}_rev'.format(repo.name), repo.version))

        diffs = []
        actuals = []
        for repo_name, arg_name, default in branches:
            actual = getattr(args, arg_name, None)
            actuals.append((repo_name, actual or default))
            if actual and actual != default:
                diffs.append("'{}' repo: {} != {}".format(repo_name, default, actual))

        if diffs:
            message = (
                "Whoa there bud! You're deploying non-default. "
                "\n{}\n"
                "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
            ).format('/n'.join(diffs))
            if not ask(message, quiet=quiet):
                exit(-1)

        return actuals

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


def _warn_no_formplayer():
    print(color_notice(dedent("""
        Formplayer will not be deployed right now, but we recommend deploying
        formplayer about once a month as well.
        It causes about 1 minute of service interruption to Web Apps and App
        Preview, but keeps these services up to date.
        You can do so by running `commcare-cloud <env> deploy formplayer`
    """)))


def mail_admins(environment, subject, message):
    if environment.fab_settings_config.email_enabled:
        commcare_cloud(
            environment.name, 'django-manage', 'mail_admins',
            '--subject', subject,
            message,
            '--environment', environment.meta_config.deploy_env
        )
