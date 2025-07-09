from datetime import datetime
from textwrap import dedent

from commcare_cloud.cli_utils import check_branch
from commcare_cloud.colors import color_notice, color_warning, color_error
from commcare_cloud.commands.ansible.run_module import BadAnsibleResult
from commcare_cloud.const import DATE_FMT
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.commands.deploy.commcare import deploy_commcare, get_commcare_deploy_diff
from commcare_cloud.commands.deploy.formplayer import deploy_formplayer, get_formplayer_deploy_diff
from commcare_cloud.environment.main import get_environment


class ZeroOrMore(list):
    # HACK work around `nargs='*', choices=[...]` produces
    # "error: invalid choice: [] (choose from ...)" when no value is provided
    def __contains__(self, item):
        return item == [] or super().__contains__(item)


class Deploy(CommandBase):
    command = 'deploy'
    help = (
        "Deploy CommCare"
    )

    arguments = (
        Argument('component', nargs='*', choices=ZeroOrMore(['commcare', 'formplayer']), help="""
            Component(s) to deploy. Default is 'commcare', or if
            always_deploy_formplayer is set in meta.yml, 'commcare formplayer'
        """),
        Argument('--resume', metavar="RELEASE_NAME", help="""
            Rather than starting a new deploy, resume a previous release.
            This option can be used to "rollback" to a previous release.
            Use the 'list-releases' command to get valid release names.
        """),
        Argument('--private', action='store_true', help="""
            Set up a private release for running management commands.
            This option implies --limit=django_manage. Use --limit=all
            to set up a private release on all applicable hosts.
        """),
        Argument('-l', '--limit', metavar='SUBSET', help="""
            Limit selected hosts.
        """),
        Argument('--keep-days', type=int, help="""
            The number of days to keep the release before it will be purged.
        """),
        Argument('--skip-record', action='store_true', help="""
            Skip the steps involved in recording and announcing the fact of the deploy.
        """),
        Argument('--commcare-rev', help="""
            The name of the commcare-hq git branch, tag, or SHA-1 commit hash to deploy.
        """, default=None),
        Argument('--ignore-kafka-checkpoint-warning', action='store_true', help="""
            Do not block deploy if Kafka checkpoints are unavailable.
        """),
        Argument('--update-config', action='store_true', help="""
            Generate new localsettings.py rather than copying from the previous
            release.
        """),
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        environment.release_name = args.resume or datetime.utcnow().strftime(DATE_FMT)

        deploy_component = args.component
        if not deploy_component:
            deploy_component = ['commcare']
            if environment.meta_config.always_deploy_formplayer:
                deploy_component.append('formplayer')

        rc = 0
        if 'commcare' in deploy_component:
            if 'formplayer' not in deploy_component:
                _warn_no_formplayer()
            try:
                rc = deploy_commcare(environment, args, unknown_args)
            except BadAnsibleResult as e:
                print(color_error(str(e)))
                rc = 1
        if 'formplayer' in deploy_component:
            _warn_about_non_formplayer_args(args)
            if rc:
                print(color_error("Skipping formplayer because commcare failed"))
            else:
                rc = deploy_formplayer(environment, args)
        return rc


class DeployDiff(CommandBase):
    command = 'deploy-diff'
    help = (
        "Display pull requests that would be deployed on master now."
    )

    arguments = (
        Argument('component', nargs='?', choices=['commcare', 'formplayer'], default='commcare', help="""
            Component to check deploy diff for. Default is 'commcare'.
        """),
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        check_branch(args)
        environment = get_environment(args.env_name)
        environment.release_name = 'deploy-diff'
        if args.component == 'formplayer':
            diff = get_formplayer_deploy_diff(environment)
        else:
            diff = get_commcare_deploy_diff(environment, args)
        diff.print_deployer_diff()


def _warn_about_non_formplayer_args(args):
    if args.resume:
        exit(color_error("Cannot --resume formplayer deploy. Remove that option and try again."))
    for arg in [
        '--private',
        '--limit',
        '--keep-days',
        '--skip-record',
        '--commcare-rev',
        '--ignore-kafka-checkpoint-warning',
        '--update-config',
    ]:
        dest = arg.lstrip("-").replace("-", "_")
        if getattr(args, dest) not in [None, False]:
            msg = f'{arg} does not apply to a formplayer deploy and will be ignored'
            print(color_warning(msg))


def _warn_no_formplayer():
    print(color_notice(dedent("""
        Formplayer will not be deployed right now, but we recommend deploying
        formplayer about once a month as well.
        It causes about 1 minute of service interruption to Web Apps and App
        Preview, but keeps these services up to date.
        You can do so by running `commcare-cloud <env> deploy formplayer`
    """)))
