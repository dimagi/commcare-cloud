from datetime import datetime

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch
from commcare_cloud.const import DATE_FMT
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.commands.deploy.command import Deploy
from commcare_cloud.commands.deploy.commcare import deploy_commcare
from commcare_cloud.environment.main import get_environment


class PreindexViews(CommandBase):
    command = 'preindex-views'
    help = """
        Set up a private release on the first pillowtop machine and run
        preindex_everything with that release.
    """

    arguments = (
        Argument('--commcare-rev', help="""
            The name of the commcare-hq git branch, tag, or SHA-1 commit hash to deploy.
        """, default=None),
        Argument('--release', metavar="RELEASE_NAME", help="""
            Use/resume an existing release rather than creating a new one.
        """),
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        add_default_args(Deploy, args)
        check_branch(args)
        args.private = True
        args.limit = "pillowtop[0]"
        environment = get_environment(args.env_name)
        environment.release_name = args.release or datetime.utcnow().strftime(DATE_FMT)
        if args.release:
            args.resume = args.release
        rc = deploy_commcare(environment, args, ())
        if rc == 0:
            rc = commcare_cloud(
                environment.name,
                "django-manage",
                "preindex_everything",
                f"--server={args.limit}",
                f"--release={environment.release_name}",
                "--tmux",
                *["--mail"] if environment.fab_settings_config.email_enabled else [],
                *unknown_args,
            )
        return rc


def add_default_args(command_class, args):
    from argparse import ArgumentParser
    parser = ArgumentParser()
    for arg in command_class.arguments:
        action = parser.add_argument(*arg._args, **arg._kwargs)
        if not hasattr(args, action.dest):
            setattr(args, action.dest, action.default)
