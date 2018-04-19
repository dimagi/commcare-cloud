# coding: utf-8
from clint.textui import puts, colored

from commcare_cloud.environment.main import get_environment
from .command_base import CommandBase


class ValidateEnvironmentSettings(CommandBase):
    command = 'validate-environment-settings'
    help = (
        "Validate your environment's configuration files"
    )

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        try:
            environment.check()
        except Exception:
            puts(colored.red(u"✗ The environment has the following error:"))
            raise
        else:
            puts(colored.green(u"✓ The environment configuration is valid."))
