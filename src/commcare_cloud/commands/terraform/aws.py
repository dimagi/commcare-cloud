from __future__ import print_function

import json
import os
import subprocess
import textwrap

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


def get_aws_resources(environment):
    config = environment.terraform_config

    # Private IP addresses
    private_ip_query = aws_cli(environment, [
        'aws', 'ec2', 'describe-instances',
        '--filter', "Name=tag-key,Values=Name", "Name=tag-value,Values=*",
        "Name=instance-state-name,Values=running",
        "Name=tag-key,Values=Environment",
        "Name=tag-value,Values={}".format(config.environment),
        "--query",
        "Reservations[*].Instances[*][Tags[?Key=='Name'].Value, NetworkInterfaces[0].PrivateIpAddresses[0].PrivateIpAddress]",
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

    elasticache_address = aws_cli(environment, [
        'aws', 'elasticache', 'describe-cache-clusters', '--show-cache-node-info',
        '--query', 'CacheClusters[0].CacheNodes[0].Endpoint.Address',
        '--output', 'json', '--region', config.region,
    ])

    resources = {}
    for name, ip in name_private_ip_pairs:
        resources[name] = ip

    for name, ip in name_public_ip_pairs:
        resources['{}.public_ip'.format(name)] = ip

    if elasticache_address:
        resources['redis-{}'.format(config.environment)] = elasticache_address

    return resources


class AwsList(CommandBase):
    command = 'aws-list'
    help = "List endpoints (ec2, rds, etc.) on AWS"

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        resources = get_aws_resources(environment)
        for name, address in sorted(resources.items()):
            print('{}\t{}'.format(address, name))
        return 0


class AwsFillInventory(CommandBase):
    command = 'aws-fill-inventory'
    help = "Fill inventory.ini.j2 using existing AWS resources"

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        resources = get_aws_resources(environment)
        with open(environment.paths.inventory_ini_j2) as f:
            inventory_ini_j2 = f.read()

        openvpn_ini_j2 = textwrap.dedent("""
        [openvpn]
        {{ vpn-staging }}

        [openvpn_public]
        {{ vpn-staging.public_ip }}
        """)

        todo = [(inventory_ini_j2, environment.paths.inventory_ini)]
        if 'vpn-{}'.format(environment.terraform_config.environment) in resources:
            todo.append((openvpn_ini_j2, environment.paths.openvpn_ini))

        for template_string, outfile in todo:
            out_string = template_string
            for name, address in resources.items():
                out_string = out_string.replace('{{ ' + name + ' }}', address)

            with open(outfile, 'w') as f:
                f.write(out_string)
