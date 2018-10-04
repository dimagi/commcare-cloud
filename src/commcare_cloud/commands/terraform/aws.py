from __future__ import print_function

import json
import os
import subprocess

from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment


def check_output(cmd_parts, env):

    env_vars = os.environ.copy()
    env_vars.update(env)
    cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
    print_command('{} {}'.format(
        ' '.join('{}={}'.format(key, value) for key, value in env.items()),
        cmd,
    ))
    return subprocess.check_output(cmd_parts, env=env_vars)


def aws_cli(environment, cmd_parts):
    return json.loads(
        check_output(cmd_parts, env={'AWS_PROFILE': environment.terraform_config.aws_profile}))


class AwsList(CommandBase):
    command = 'aws-list'
    help = "List endpoints (ec2, rds, etc.) on AWS"

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        config = environment.terraform_config

        # Private IP addresses
        private_ip_query = aws_cli(environment, [
            'aws', 'ec2', 'describe-instances',
            '--filter', "Name=tag-key,Values=Name", "Name=tag-value,Values=*",
            "Name=instance-state-name,Values=running",
            "Name=tag-key,Values=Environment",
            "Name=tag-value,Values={}".format(config.environment),
            "--query", "Reservations[*].Instances[*][Tags[?Key=='Name'].Value, NetworkInterfaces[0].PrivateIpAddresses[0].PrivateIpAddress]",
            "--output", "json",
            "--region", config.region,
        ])
        name_private_ip_pairs = [(item[0][0][0], item[0][1]) for item in private_ip_query]

        # Public IP addresses
        public_ip_query = aws_cli(environment, [
            'aws', 'ec2', 'describe-instances',
            '--filter', "Name=tag-key,Values=Name", "Name=tag-value,Values=*",
            "Name=instance-state-name,Values=running",
            "Name=tag-key,Values=Environment",
            "Name=tag-value,Values={}".format(config.environment),
            "--query",
            "Reservations[*].Instances[*][Tags[?Key=='Name'].Value[],NetworkInterfaces[0].Association.PublicIp]",
            "--output", "json",
            "--region", config.region,
        ])
        name_public_ip_pairs = [(item[0][0][0], item[0][1]) for item in public_ip_query
                                if item[0][1] is not None]

        elasticache_query = aws_cli(environment, [
            'aws', 'elasticache', 'describe-cache-clusters', '--show-cache-node-info',
            '--query', 'CacheClusters[0].CacheNodes[0].Endpoint.Address',
            '--output', 'json', '--region', config.region,
        ])

        for name, ip in name_private_ip_pairs:
            print('{}\t{}'.format(ip, name))

        for name, ip in name_public_ip_pairs:
            print('{}\t{}.public_ip'.format(ip, name))

        if elasticache_query:
            print('{}\tredis-{}'.format(elasticache_query, config.environment))
        return 0
