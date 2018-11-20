# coding=utf-8
from __future__ import print_function

import getpass
import json
import os
import subprocess
import textwrap
from datetime import datetime

import boto3
import six
import yaml
from clint.textui import puts, colored
from memoized import memoized
from six.moves import shlex_quote
from six.moves import configparser
from six.moves import input

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase, Argument
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
        check_output(cmd_parts, env={'AWS_PROFILE': aws_sign_in(environment.terraform_config.aws_profile)}))


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
    help = """
        Fill inventory.ini.j2 using AWS resource values cached in aws-resources.yml

        If --cached is not specified, also refresh aws-resources.yml
        to match what is actually in AWS.
    """

    arguments = [
        Argument('--cached', action='store_true', help="""
            Use the values set in aws-resources.yml rather than fetching from AWS.

            This runs much more quickly and gives the same result, provided no changes
            have been made to our actual resources in AWS.
        """)
    ]

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        if not os.path.exists(environment.paths.inventory_ini_j2):
            print("Env {} not using templated inventory (inventory.ini.j2). Skipping"
                  .format(args.env_name))
            return 0

        if not args.cached:
            resources = get_aws_resources(environment)
            with open(environment.paths.aws_resources_yml, 'w') as f:
                f.write(yaml.safe_dump(resources, default_flow_style=False))
        else:
            with open(environment.paths.aws_resources_yml, 'r') as f:
                resources = yaml.load(f.read())

        with open(environment.paths.inventory_ini_j2) as f:
            inventory_ini_j2 = f.read()

        env_suffix = environment.terraform_config.environment
        vpn_name = 'vpn-{}'.format(env_suffix)
        openvpn_ini_j2 = textwrap.dedent("""
        [openvpn]
        {{ %(vpn_name)s }}  # ansible_host={{ %(vpn_name)s.public_ip }}

        [openvpn:vars]
        subdomain_name={{ vpn_subdomain_name }}
        hostname=%(vpn_name)s
        """ % {'vpn_name': vpn_name})

        if vpn_name in resources:
            inventory_ini_j2 += openvpn_ini_j2
            resources["vpn_subdomain_name"] = "vpn.{}".format(environment.proxy_config.SITE_HOST)

        out_string = inventory_ini_j2
        for name, address in resources.items():
            out_string = out_string.replace('{{ ' + name + ' }}', address)

        with open(environment.paths.inventory_ini, 'w') as f:
            f.write(out_string)


DEFAULT_SIGN_IN_DURATION_MINUTES = 30


class StringIsGuess(six.text_type):
    def __new__(cls, *args, **kwargs):
        is_guess = kwargs.pop('is_guess')
        self = super(StringIsGuess, cls).__new__(cls, *args, **kwargs)
        self.is_guess = is_guess
        return self


@memoized
def get_default_username():
    """
    Returns a special string type that has field is_guess

    If is_guess is True, the caller should assume the user wants this value
    and should not give them a chance to change their choice of user interactively.
    """
    environ_username = os.environ.get('COMMCARE_CLOUD_DEFAULT_USERNAME')
    if environ_username:
        return StringIsGuess(environ_username, is_guess=False)
    else:
        return StringIsGuess(getpass.getuser(), is_guess=True)


def print_help_message_about_the_commcare_cloud_default_username_env_var(username):
    puts(colored.blue("Did you know? You can put"))
    puts(colored.blue("    export COMMCARE_CLOUD_DEFAULT_USERNAME={}".format(username)))
    puts(colored.blue("in your profile to never have to type that in again! 🌈"))


class AwsSignIn(CommandBase):
    command = 'aws-sign-in'
    help = """
        Use your MFA device to "sign in" to AWS for <duration> minutes (default {})

        This will store the temporary session credentials in ~/.aws/credentials
        under a profile named with the pattern "<aws_profile>:profile".
        After this you can use other AWS-related commands for up to <duration> minutes
        before having to sign in again.
    """.format(DEFAULT_SIGN_IN_DURATION_MINUTES)

    arguments = [
        Argument('--duration-minutes', type=int, default=DEFAULT_SIGN_IN_DURATION_MINUTES, help="""
            Stay signed in for this many minutes
        """)
    ]

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        duration_minutes = args.duration_minutes
        aws_profile = environment.terraform_config.aws_profile
        aws_sign_in(aws_profile, duration_minutes, force_new=True)


@memoized
def aws_sign_in(aws_profile, duration_minutes=DEFAULT_SIGN_IN_DURATION_MINUTES,
                force_new=False):
    """
    Create a temp session through MFA for a given aws profile

    :param aws_profile: The name of an existing aws profile to create a temp session for
    :param duration_minutes: How long to set the session expiration if a new one is created
    :param force_new: If set to True, creates new credentials even if valid ones are found
    :return: The name of temp session profile.
             (Always the passed in profile followed by ':session')
    """
    aws_session_profile = '{}:session'.format(aws_profile)
    if not force_new \
            and _has_valid_session_credentials(aws_session_profile):
        return aws_session_profile

    default_username = get_default_username()
    if default_username.is_guess:
        username = input("Enter username associated with credentials [{}]: ".format(
            default_username)) or default_username
        print_help_message_about_the_commcare_cloud_default_username_env_var(username)
    else:
        username = default_username
    mfa_token = input("Enter your MFA token: ")
    generate_session_profile(aws_profile, username, mfa_token, duration_minutes)

    puts(colored.green(u"✓ Sign in accepted"))
    puts(colored.cyan(
        "You will be able to use AWS from the command line for the next {} minutes."
        .format(duration_minutes)))
    puts(colored.cyan(
        "To use this session outside of commcare-cloud, "
        "prefix your command with AWS_PROFILE={}:session".format(aws_profile)))
    return aws_session_profile


def generate_session_profile(aws_profile, username, mfa_token, duration_minutes):
    # General idea from https://www.vividcortex.com/blog/setting-up-multi-factor-authentication-with-the-aws-cli
    boto_session = boto3.session.Session(profile_name=aws_profile)
    iam = boto_session.client('iam')
    devices = iam.list_mfa_devices(UserName=username)['MFADevices']
    device_arn = sorted(devices, key=lambda device: device['EnableDate'])[-1]['SerialNumber']
    sts = boto_session.client('sts')
    credentials = sts.get_session_token(
        SerialNumber=device_arn,
        TokenCode=mfa_token,
        DurationSeconds=duration_minutes * 60,
    )['Credentials']
    _write_credentials_to_aws_credentials(
        '{}:session'.format(aws_profile),
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        expiration=credentials['Expiration'],
    )


def _write_credentials_to_aws_credentials(
        aws_profile, aws_access_key_id, aws_secret_access_key, aws_session_token,
        expiration,
        aws_credentials_path=os.path.expanduser('~/.aws/credentials')):
    # followed code examples from https://gist.github.com/incognick/c121038dbd2180c683fda6ae5e30cba3
    config = configparser.ConfigParser()
    config.read(os.path.realpath(aws_credentials_path))
    if aws_profile not in config.sections():
        config.add_section(aws_profile)
    config.set(aws_profile, 'aws_access_key_id', aws_access_key_id)
    config.set(aws_profile, 'aws_secret_access_key', aws_secret_access_key)
    config.set(aws_profile, 'aws_session_token', aws_session_token)
    config.set(aws_profile, 'expiration', expiration.strftime("%Y-%m-%dT%H:%M:%SZ"))
    with open(aws_credentials_path, 'w') as f:
        config.write(f)


def _has_valid_session_credentials(
        aws_profile, aws_credentials_path=os.path.expanduser('~/.aws/credentials')):
    config = configparser.ConfigParser()
    config.read(os.path.realpath(aws_credentials_path))
    if aws_profile not in config.sections():
        return False
    try:
        expiration = datetime.strptime(config.get(aws_profile, 'expiration'), "%Y-%m-%dT%H:%M:%SZ")
    except configparser.NoOptionError:
        return False

    return datetime.utcnow() < expiration

