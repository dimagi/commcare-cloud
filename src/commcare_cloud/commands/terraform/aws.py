from __future__ import print_function

import json
import os
import subprocess

from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment


class AwsList(CommandBase):
    command = 'aws-list'
    help = "List endpoints (ec2, rds, etc.) on AWS"

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        config = environment.terraform_config
        cmd_parts = [
            'aws', 'ec2', 'describe-instances',
            '--filter', "Name=tag-key,Values=Name", "Name=tag-value,Values=*",
            "Name=instance-state-name,Values=running",
            "Name=tag-key,Values=Environment",
            "Name=tag-value,Values={}".format(config.environment),
            "--query", "Reservations[*].Instances[*][Tags[?Key=='Name'].Value, NetworkInterfaces[0].PrivateIpAddresses[0].PrivateIpAddress]",
            "--output", "json",
            "--region", config.region,
        ]

        env_vars = {'AWS_PROFILE': environment.terraform_config.aws_profile}
        all_env_vars = os.environ.copy()
        all_env_vars.update(env_vars)
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command('{} {}'.format(
            ' '.join('{}={}'.format(key, value) for key, value in env_vars.items()),
            cmd,
        ))
        raw_list = json.loads(subprocess.check_output(cmd_parts, env=all_env_vars, stdin=subprocess.PIPE))
        nice_list = [(item[0][0][0], item[0][1]) for item in raw_list]
        for name, ip in nice_list:
            print('{}\t{}'.format(ip, name))
        return 0
