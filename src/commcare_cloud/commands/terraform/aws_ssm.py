import subprocess

import yaml

from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.terraform.aws import aws_cli, aws_sign_in
from commcare_cloud.environment.main import get_environment


class AwsSsmStartSession(CommandBase):
    command = 'aws-ssm-start-session'
    help = "Wrapper for `aws ssm start-session`"

    arguments = [
        Argument('target', help="The host to start a session on")
    ]

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        with open(environment.paths.aws_resources_yml, 'r') as f:
            resources = yaml.safe_load(f.read())
        instance_id = resources['{}-{}.instance_id'.format(args.target, args.env_name)]
        self._aws_cli(environment, [
            '/usr/local/bin/aws', 'ssm', 'start-session', '--target', instance_id
        ])

    @staticmethod
    def _aws_cli(environment, cmd_parts):
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        return subprocess.call(cmd_parts, env={'AWS_PROFILE': aws_sign_in(environment)})
