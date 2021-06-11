from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import sys
from textwrap import dedent

from commcare_cloud.cli_utils import check_branch
from commcare_cloud.colors import color_notice, color_warning, color_error
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.commands.deploy.commcare import deploy_commcare
from commcare_cloud.commands.deploy.formplayer import deploy_formplayer
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs
from commcare_cloud.fab.utils import retrieve_cached_deploy_env


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
        if len(sys.argv) <= 1:
            # No environment specified, so no need to add environment-specific repositories
            return

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
        if args.resume:
            try:
                # use cached env to ensure consistency with last deploy
                cached_fab_env = retrieve_cached_deploy_env(environment.deploy_env)
            except Exception:
                print(color_error('Unable to resume deploy, please start anew'))
            else:
                environment = cached_fab_env.ccc_environment

        deploy_component = args.component
        if not deploy_component:
            deploy_component = ['commcare']
            if environment.meta_config.always_deploy_formplayer:
                deploy_component.append('formplayer')

        rc = 0
        if 'commcare' in deploy_component:
            if 'formplayer' not in deploy_component:
                _warn_no_formplayer()
            rc = deploy_commcare(environment, args, unknown_args)
        if 'formplayer' in deploy_component:
            if 'commcare' not in deploy_component:
                if args.commcare_rev:
                    print(color_warning('--commcare-rev does not apply to a formplayer deploy and will be ignored'))
                if args.fab_settings:
                    print(color_warning('--set does not apply to a formplayer deploy and will be ignored'))
            if rc:
                print(color_error("Skipping formplayer because commcare failed"))
            else:
                rc = deploy_formplayer(environment, args)
        return rc


def _warn_no_formplayer():
    print(color_notice(dedent("""
        Formplayer will not be deployed right now, but we recommend deploying
        formplayer about once a month as well.
        It causes about 1 minute of service interruption to Web Apps and App
        Preview, but keeps these services up to date.
        You can do so by running `commcare-cloud <env> deploy formplayer`
    """)))
