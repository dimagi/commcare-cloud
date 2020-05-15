# coding=utf-8
from __future__ import print_function

import getpass
import json
import os
import subprocess
import textwrap
from datetime import datetime

import boto3
import jinja2
import six
import yaml
from clint.textui import puts
from memoized import memoized
from simplejson import JSONDecodeError
from six.moves import shlex_quote
from six.moves import configparser
from six.moves import input

from commcare_cloud.cli_utils import print_command
from commcare_cloud.colors import color_success, color_notice
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment


def check_output(cmd_parts, env, silent=False):

    env_vars = os.environ.copy()
    env_vars.update(env)
    if not silent:
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command('{} {}'.format(
            ' '.join('{}={}'.format(key, value) for key, value in env.items()),
            cmd,
        ))
    return subprocess.check_output(cmd_parts, env=env_vars)


def aws_cli(environment, cmd_parts):

    return json.loads(
        check_output(cmd_parts, env={'AWS_PROFILE': aws_sign_in(environment)}))


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

    rds_endpoints = aws_cli(environment, [
        'aws', 'rds', 'describe-db-instances',
        '--query', 'DBInstances[*].[DBInstanceIdentifier,Endpoint.Address]',
        '--output', 'json', '--region', config.region,
    ])

    resources = {}
    for name, ip in name_private_ip_pairs:
        resources[name] = ip

    for name, ip in name_public_ip_pairs:
        resources['{}.public_ip'.format(name)] = ip

    for name, endpoint in rds_endpoints:
        assert name not in resources
        resources[name] = endpoint

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
                resources = yaml.safe_load(f.read())

        with open(environment.paths.inventory_ini_j2) as f:
            inventory_ini_j2 = f.read()

        with open(environment.paths.inventory_ini, 'w') as f:
            # by putting this inside the with
            # we make sure that if the it fails, inventory.ini is made empty
            # reflecting that we were unable to create it
            out_string = AwsFillInventoryHelper(environment, inventory_ini_j2,
                                                resources).render()
            f.write(out_string)


class AwsFillInventoryHelper(object):
    def __init__(self, environment, inventory_ini_j2, resources):
        self.environment = environment
        self.inventory_ini_j2 = inventory_ini_j2
        self.resources = resources

    def render(self):
        return jinja2.Template(self.template, keep_trailing_newline=True).render(self.context)

    @property
    def template(self):
        template = self.inventory_ini_j2
        if self.vpn_name in self.resources:
            template += self.openvpn_ini_j2
        return template

    @property
    def context(self):
        context = {
            'aws_resources': self.resources,
            'vpn_subdomain_name': "vpn.{}".format(self.environment.proxy_config.SITE_HOST)
        }

        servers = self.environment.terraform_config.servers + self.environment.terraform_config.proxy_servers
        for server in servers:
            is_bionic = server.os == 'bionic'
            inventory_vars = [
                ('hostname', server.server_name),
                ('ufw_private_interface', ('ens5' if is_bionic else 'eth0')),
                ('ansible_python_interpreter', ('/usr/bin/python3' if is_bionic else None)),
            ]
            if server.block_device:
                inventory_vars.extend([
                    ('datavol_device', '/dev/sdf'),
                    ('datavol_device1', '/dev/sdf'),
                    ('is_datavol_ebsnvme', 'yes'),
                ])
                if server.block_device.encrypted:
                    inventory_vars.append(
                        ('root_encryption_mode', 'aws'),
                    )

            context.update(
                self.get_host_group_definition(resource_name=server.server_name, vars=inventory_vars)
            )

        for rds_instance in self.environment.terraform_config.rds_instances:
            context.update(
                self.get_host_group_definition(resource_name=rds_instance.identifier, prefix='rds_')
            )
        return context

    @property
    def env_suffix(self):
        return self.environment.terraform_config.environment

    @property
    def vpn_name(self):
        return 'vpn-{}'.format(self.env_suffix)

    @property
    def openvpn_ini_j2(self):
        return textwrap.dedent("""
        [openvpn]
        {{ aws_resources['%(vpn_name)s'] }}  # ansible_host={{ aws_resources['%(vpn_name)s.public_ip'] }}

        [openvpn:vars]
        subdomain_name={{ vpn_subdomain_name }}
        hostname=%(vpn_name)s
        """ % {'vpn_name': self.vpn_name})

    def get_host_group_definition(self, resource_name, vars=(), prefix=''):
        context = {}
        host_name = resource_name.split('-', 1)[0]
        name_matches = '{}-{}'.format(host_name, self.env_suffix) == resource_name
        if resource_name in self.resources and name_matches:
            group_name = '{}{}'.format(prefix, host_name)
            context['__{}__'.format(group_name)] = ''.join([
                '[{}]\n'.format(group_name),
                self.resources[resource_name],
            ]) + ''.join([' {}={}'.format(key, value) for key, value in vars if value])
        return context


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
    puts(color_notice("Did you know? You can put"))
    puts(color_notice("    export COMMCARE_CLOUD_DEFAULT_USERNAME={}".format(username)))
    puts(color_notice("in your profile to never have to type that in again! 🌈"))


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
        aws_sign_in(environment, duration_minutes, force_new=True)


@memoized
def aws_sign_in(environment, duration_minutes=DEFAULT_SIGN_IN_DURATION_MINUTES, force_new=False):
    if environment.aws_config.credential_style == 'sso':
        return _aws_sign_in_with_sso(environment)
    else:
        return _aws_sign_in_with_iam(environment.terraform_config.aws_profile, duration_minutes=duration_minutes,
                                     force_new=force_new)


@memoized
def _aws_sign_in_with_sso(environment):
    """
    Create a temp session through MFA for a given aws profile

    :param aws_profile: The name of an existing aws profile to create a temp session for
    :param duration_minutes: How long to set the session expiration if a new one is created
    :param force_new: If set to True, creates new credentials even if valid ones are found
    :return: The name of temp session profile.
             (Always the passed in profile followed by ':session')
    """
    aws_session_profile = '{}:session'.format(environment.terraform_config.aws_profile)
    # todo: add `... or if _date_modified(aws_config_path) > _date_modified(aws_credentials_path)`
    if not _has_profile_for_sso(aws_session_profile):
        puts(color_notice("Configuring SSO. To further customize, run `aws configure sso --profile {}`".format(aws_session_profile)))
        _write_profile_for_sso(
            aws_session_profile,
            sso_start_url=environment.aws_config.sso_config.sso_start_url,
            sso_account_id=environment.aws_config.sso_config.sso_account_id,
            sso_region=environment.aws_config.sso_config.sso_region,
            region=environment.aws_config.sso_config.region,
        )

    if not _has_valid_session_credentials_for_sso():
        check_output(['aws', 'sso', 'login'], env={'AWS_PROFILE': aws_session_profile})

    if not _has_valid_v1_session_credentials(aws_session_profile):
        _sync_sso_to_v1_credentials(aws_session_profile)

    return aws_session_profile


def _sync_sso_to_v1_credentials(aws_session_profile):
    caller_identity = _get_caller_identity({'AWS_PROFILE': aws_session_profile})
    if not caller_identity:
        raise ValueError((
            "SSO profile mis-configured and cannot fix automatically. "
            "Edit [profile {}] in ~/.aws/config manually; "
            "to start over, remove it from the file manually and try again.").format(aws_session_profile))
    # Until this is built in to aws, we need this insane workaround to get backwards compatibility
    # with the credential format that terraform uses
    cli_cache_dir = os.path.expanduser('~/.aws/cli/cache/')

    for filepath in _iter_files_in_dir(cli_cache_dir):
        with open(filepath) as f:
            try:
                data = json.load(f)
            except JSONDecodeError:
                continue
            else:
                if data.get('ProviderType') != 'sso':
                    continue
                credentials = data['Credentials']
                comparison = _get_caller_identity({
                    'AWS_ACCESS_KEY_ID': credentials.get('AccessKeyId'),
                    'AWS_SECRET_ACCESS_KEY': credentials.get('SecretAccessKey'),
                    'AWS_SESSION_TOKEN': credentials.get('SessionToken'),
                })
                if comparison == caller_identity:
                    break
    else:
        raise ValueError((
            "Unable to find cached credentials immediately after SSO. "
            "There aren't known ways for this to happen, so this will require debugging."))

    _write_credentials_to_aws_credentials(
        aws_session_profile,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        expiration=datetime.strptime(credentials['Expiration'], "%Y-%m-%dT%H:%M:%SUTC"),
    )


def _get_caller_identity(env_vars):
    try:
        caller_identity = check_output(['aws', 'sts', 'get-caller-identity'], env=env_vars,
                                       # This call isn't really useful to the commcare-cloud user
                                       # and is sometimes called with explicit credentials
                                       # that we don't want to print to the screen.
                                       silent=True)
    except subprocess.CalledProcessError as e:
        # 255: Not logged in / missing credentials
        # 254: "The security token included in the request is expired"
        if e.returncode not in (255, 254):
            raise
        # this means we're not signed in
        return None
    else:
        return caller_identity


@memoized
def _aws_sign_in_with_iam(aws_profile, duration_minutes=DEFAULT_SIGN_IN_DURATION_MINUTES, force_new=False):
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
            and _has_valid_v1_session_credentials(aws_session_profile):
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

    puts(color_success(u"✓ Sign in accepted"))
    puts("You will be able to use AWS from the command line for the next {} minutes."
         .format(duration_minutes))
    puts(color_notice(
        "To use this session outside of commcare-cloud, "
        "prefix your command with AWS_PROFILE={}:session".format(aws_profile)))
    return aws_session_profile


def generate_session_profile(aws_profile, username, mfa_token, duration_minutes):
    # General idea from https://www.vividcortex.com/blog/setting-up-multi-factor-authentication-with-the-aws-cli
    boto_session = boto3.session.Session(profile_name=aws_profile)
    iam = boto_session.client('iam')

    if username == 'root':
        devices = [device for device in iam.list_mfa_devices()['MFADevices']
                   if 'root-account-mfa-device' in device['SerialNumber']]
    else:
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


def _has_profile_for_sso(
        aws_profile, aws_config_path=os.path.expanduser('~/.aws/config')):
    config = configparser.ConfigParser()
    config.read(os.path.realpath(aws_config_path))
    section = 'profile {}'.format(aws_profile)

    if section not in config.sections():
        return False

    try:
        config.get(section, 'sso_start_url')
    except configparser.NoOptionError:
        return False
    else:
        return True


def _write_profile_for_sso(
        aws_profile,
        sso_start_url,
        sso_region,
        sso_account_id,
        region,
        aws_config_path=os.path.expanduser('~/.aws/config')):
    config = configparser.ConfigParser()
    config.read(os.path.realpath(aws_config_path))
    section = 'profile {}'.format(aws_profile)

    if section not in config.sections():
        config.add_section(section)
    config.set(section, 'sso_start_url', sso_start_url)
    config.set(section, 'sso_region', sso_region)
    config.set(section, 'sso_account_id', sso_account_id)
    config.set(section, 'sso_role_name', 'AWSPowerUserAccess')
    config.set(section, 'region', region)
    config.set(section, 'output', 'json')
    with open(aws_config_path, 'w') as f:
        config.write(f)


def _has_valid_session_credentials_for_sso(aws_sso_cache_path=os.path.expanduser('~/.aws/sso/cache/')):
    for filepath in _iter_files_in_dir(aws_sso_cache_path):
        try:
            with open(filepath, 'r') as f:
                contents = json.load(f)
        except JSONDecodeError:
            continue
        else:
            if 'startUrl' in contents and 'expiresAt' in contents:
                expiration = datetime.strptime(contents['expiresAt'], "%Y-%m-%dT%H:%M:%SUTC")
                return datetime.utcnow() < expiration
    return False


def _has_valid_v1_session_credentials(
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


def _iter_files_in_dir(directory):
    """
    Yield each filepath under a directory path that corresponds to a file (not a dir)
    """
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            yield filepath
