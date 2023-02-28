# coding=utf-8
from __future__ import absolute_import, print_function, unicode_literals

import json
import os
import subprocess
import textwrap
from datetime import datetime
from dateutil import parser
import pytz
from io import open

import boto3
import jinja2
import requests
import yaml
from clint.textui import puts
from memoized import memoized
from simplejson import JSONDecodeError
from six.moves import configparser, input, shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.colors import color_notice, color_success
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.user_utils import get_default_username, \
    print_help_message_about_the_commcare_cloud_default_username_env_var
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
    ec2_instances_query = aws_cli(environment, [
        'aws', 'ec2', 'describe-instances',
        '--filter', "Name=tag-key,Values=Name", "Name=tag-value,Values=*",
        "Name=instance-state-name,Values=running",
        "Name=tag-key,Values=Environment",
        "Name=tag-value,Values={}".format(config.environment),
        "--query",
        ("Reservations[*].Instances[*]["
         "Tags[?Key=='Name'].Value, "
         "NetworkInterfaces[0].PrivateIpAddresses[0].PrivateIpAddress, "
         "NetworkInterfaces[0].Association.PublicIp, "
         "InstanceId"
         "]"),
        "--output", "json",
        "--region", config.region,
    ])
    ec2_instances_info = [{
        'name': item[0][0][0],
        'private_ip': item[0][1],
        'public_ip': item[0][2],
        'instance_id': item[0][3],
    } for item in ec2_instances_query]

    rds_endpoints = aws_cli(environment, [
        'aws', 'rds', 'describe-db-instances',
        '--query', 'DBInstances[*].[DBInstanceIdentifier,Endpoint.Address]',
        '--output', 'json', '--region', config.region,
    ])

    awsmq_info = [{
        'brokerid': brokerid,
        'brokername': brokername,
        'endpoint': '{brokerid}.mq.{config.region}.amazonaws.com:5671'.format(brokerid=brokerid, config=config)
    } for brokername, brokerid in aws_cli(environment, [
        'aws', 'mq', 'list-brokers',
        '--query', 'BrokerSummaries[*].[BrokerName,BrokerId]',
        "--output", "json",
        "--region", config.region,
    ])]


    nlb_endpoints = aws_cli(environment, [
        'aws', 'elbv2', 'describe-load-balancers',
        '--query', "LoadBalancers[?Type=='network'].[LoadBalancerName,DNSName]",
        '--output', 'json', '--region', config.region,
    ])

    alb_endpoints = aws_cli(environment, [
        'aws', 'elbv2', 'describe-load-balancers',
        '--query', "LoadBalancers[?Type=='application'].[LoadBalancerName,DNSName]",
        '--output', 'json', '--region', config.region,
    ])

    efs_info = [{
        'name': name,
        'efs_id': efs_id,
        'efs_dns': '{efs_id}.efs.{config.region}.amazonaws.com'.format(efs_id=efs_id, config=config)
    } for (name,), efs_id in aws_cli(environment, [
        'aws', 'efs', 'describe-file-systems', '--query', "FileSystems[*][Tags[?Key=='Name'].Value,FileSystemId]",
        "--output", "json",
        "--region", config.region,
    ])]

    fsx_info = [{
        'name': name,
        'fsx_id': fsx_id,
        'fsx_dns': '{fsx_id}.fsx.{config.region}.amazonaws.com'.format(fsx_id=fsx_id, config=config)
    } for (name,), fsx_id in aws_cli(environment, [
        'aws', 'fsx', 'describe-file-systems', '--query', "FileSystems[*][Tags[?Key=='Name'].Value,FileSystemId]",
        "--output", "json",
        "--region", config.region,
    ])]

    resources = {}
    for info in ec2_instances_info:
        name = info['name']
        resources[name] = info['private_ip']
        if info['public_ip']:
            resources['{}.public_ip'.format(name)] = info['public_ip']
        resources['{}.instance_id'.format(name)] = info['instance_id']

    for name, endpoint in rds_endpoints:
        assert name not in resources
        resources[name] = endpoint

    for name, endpoint in nlb_endpoints:
        assert name not in resources
        resources[name.replace('-nlb-', '_nlb-')] = endpoint

    for name, endpoint in alb_endpoints:
        assert name not in resources
        resources[name.replace('-alb-', '_alb-')] = endpoint

    for info in efs_info:
        resources['{name}-efs'.format(**info)] = info['efs_dns']

    for info in fsx_info:
        resources['{name}-fsx'.format(**info)] = info['fsx_dns']

    for info in awsmq_info:
        resources[info['brokername']] = info['endpoint']

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
            with open(environment.paths.aws_resources_yml, "w", encoding="utf-8") as f:
                f.write(yaml.safe_dump(resources, default_flow_style=False))
        else:
            with open(environment.paths.aws_resources_yml, 'r', encoding='utf-8') as f:
                # PY2: yaml.safe_load will return bytes when the content is ASCII-only bytes
                resources = yaml.safe_load(f.read())

        with open(environment.paths.inventory_ini_j2, 'r', encoding='utf-8') as f:
            inventory_ini_j2 = f.read()

        with open(environment.paths.inventory_ini, 'w', encoding='utf-8') as f:
            # by putting this inside the with
            # we make sure that if the it fails, inventory.ini is made empty
            # reflecting that we were unable to create it
            out_string = AwsFillInventoryHelper(environment, inventory_ini_j2,
                                                resources).render()
            # PY2: out_string is unicode based on Jinja2 render method
            f.write(out_string)


class AwsFillInventoryHelper(object):
    def __init__(self, environment, inventory_ini_j2, resources):
        self.environment = environment
        self.template = inventory_ini_j2
        self.resources = resources

    def render(self):
        return jinja2.Template(self.template, keep_trailing_newline=True).render(self.context)

    @property
    def context(self):
        context = {
            'aws_resources': self.resources,
        }

        servers = self.environment.terraform_config.servers + self.environment.terraform_config.proxy_servers
        for server_spec in servers:
            for server_name in server_spec.get_all_server_names():
                inventory_vars = [
                    ('hostname', server_name.replace('_', '-')),
                    ('ufw_private_interface', 'ens5'),
                    ('ansible_python_interpreter', '/usr/bin/python3'),
                    ('ec2_instance_id', self.resources['{}.instance_id'.format(server_name)])
                ]
                if server_spec.block_device:
                    inventory_vars.extend([
                        ('datavol_device', '/dev/sdf'),
                        ('datavol_device1', '/dev/sdf'),
                        ('is_datavol_ebsnvme', 'yes'),
                    ])
                    if server_spec.block_device.encrypted:
                        inventory_vars.append(
                            ('root_encryption_mode', 'aws'),
                        )
                elif server_spec.volume_encrypted:
                    inventory_vars.append(
                        ('root_encryption_mode', 'aws'),
                    )

                context.update(
                    self.get_host_group_definition(resource_name=server_name, vars=inventory_vars)
                )
            if server_spec.count is not None:
                context.update(
                    self.get_multi_host_group_definition(
                        server_spec.get_host_group_name(), server_spec.get_all_host_names(),
                        existing_context=context
                    )
                )

        for rds_instance in self.environment.terraform_config.rds_instances:
            context.update(
                self.get_host_group_definition(resource_name=rds_instance.identifier, prefix='rds_')
            )

        for pgbouncer_nlb in self.environment.terraform_config.pgbouncer_nlbs:
            context.update(
                self.get_host_group_definition(resource_name=pgbouncer_nlb.name)
            )

        for internal_alb in self.environment.terraform_config.internal_albs:
            context.update(
                self.get_host_group_definition(resource_name=internal_alb.name)
            )

        return context

    @property
    def env_suffix(self):
        return self.environment.terraform_config.environment

    @property
    def vpn_name(self):
        return 'vpn-{}'.format(self.env_suffix)

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

    def get_multi_host_group_definition(self, host_group_name, host_names, existing_context):
        context = {}
        context['__{}__'.format(host_group_name)] = '\n'.join([
            existing_context['__{}__'.format(host_name)]
            for host_name in host_names
        ]) + '\n[{}:children]\n'.format(host_group_name) + '\n'.join([
            host_name for host_name in host_names
        ])
        return context


DEFAULT_SIGN_IN_DURATION_MINUTES = 30


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


AWS_CREDENTIALS_PATH = os.path.expanduser('~/.aws/credentials')
AWS_CONFIG_PATH = os.path.expanduser('~/.aws/config')
AWS_DOT_DIR = os.path.expanduser('~/.aws/')
AWS_SSO_CACHE_DIR = os.path.expanduser('~/.aws/sso/cache/')
AWS_CLI_CACHE_DIR = os.path.expanduser('~/.aws/cli/cache/')


def is_aws_env(environment):
    return bool(environment.terraform_config)


@memoized
def aws_sign_in(environment, duration_minutes=DEFAULT_SIGN_IN_DURATION_MINUTES, force_new=False):
    if is_ec2_instance_in_account(environment.aws_config.sso_config.sso_account_id):
        return None

    _ensure_all_dirs(AWS_DOT_DIR)
    if environment.aws_config.credential_style == 'sso':
        for path in (AWS_SSO_CACHE_DIR, AWS_CLI_CACHE_DIR):
            _ensure_all_dirs(path)
        return _aws_sign_in_with_sso(environment)
    else:
        return _aws_sign_in_with_iam(environment.terraform_config.aws_profile, duration_minutes=duration_minutes,
                                     force_new=force_new)


def is_ec2_instance_in_account(account_id):
    try:
        # AWS Metadata v2 requires multiple requests in this format as per
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html
        token_api_response = requests.put(
            'http://169.254.169.254/latest/api/token',
            timeout=0.100,
            headers={
                'X-aws-ec2-metadata-token-ttl-seconds': '21600',
            }
        )
        if token_api_response.status_code == 200:
            aws_instance_identity_doc = requests.get(
                'http://169.254.169.254/latest/dynamic/instance-identity/document',
                timeout=0.100,
                headers={'X-aws-ec2-metadata-token': token_api_response.text},
            ).json()
        else:
            return False

    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        return False

    return aws_instance_identity_doc.get('accountId') == account_id


def is_session_manager_plugin_installed():
    try:
        # swallow output
        subprocess.check_output('session-manager-plugin', shell=True)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


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
    # todo: add `... or if _date_modified(AWS_CONFIG_PATH) > _date_modified(AWS_CREDENTIALS_PATH)`
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
        _refresh_sso_credentials(aws_session_profile)

    if not _has_valid_v1_session_credentials(aws_session_profile):
        _sync_sso_to_v1_credentials(aws_session_profile)

    return aws_session_profile


def _sync_sso_to_v1_credentials(aws_session_profile):
    caller_identity = _get_caller_identity({'AWS_PROFILE': aws_session_profile})
    if not caller_identity:
        # _has_valid_session_credentials_for_sso is a mediocre heuristic,
        # so just assume it was wrong and refresh the sso credentials before failing hard
        _refresh_sso_credentials(aws_session_profile)
        caller_identity = _get_caller_identity({'AWS_PROFILE': aws_session_profile})
        if not caller_identity:
            raise ValueError((
                "SSO profile mis-configured and cannot fix automatically. "
                "Edit [profile {}] in ~/.aws/config manually; "
                "to start over, remove it from the file manually and try again.").format(aws_session_profile))
    # Until this is built in to aws, we need this insane workaround to get backwards compatibility
    # with the credential format that terraform uses

    for filepath in _iter_files_in_dir(AWS_CLI_CACHE_DIR):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except JSONDecodeError:
                continue

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
        expiration=parser.parse(credentials['Expiration']),
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

    puts(color_success("✓ Sign in accepted"))
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
        aws_profile, aws_access_key_id, aws_secret_access_key, aws_session_token, expiration):
    # followed code examples from https://gist.github.com/incognick/c121038dbd2180c683fda6ae5e30cba3
    config = configparser.ConfigParser()
    config.read(os.path.realpath(AWS_CREDENTIALS_PATH))
    if aws_profile not in config.sections():
        config.add_section(aws_profile)
    config.set(aws_profile, 'aws_access_key_id', aws_access_key_id)
    config.set(aws_profile, 'aws_secret_access_key', aws_secret_access_key)
    config.set(aws_profile, 'aws_session_token', aws_session_token)
    config.set(aws_profile, 'expiration', expiration.strftime("%Y-%m-%dT%H:%M:%SZ"))
    with open(AWS_CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        config.write(f)


def _has_profile_for_sso(aws_profile):
    config = configparser.ConfigParser()
    config.read(os.path.realpath(AWS_CONFIG_PATH))
    section = 'profile {}'.format(aws_profile)

    if section not in config.sections():
        return False

    try:
        config.get(section, 'sso_start_url')
    except configparser.NoOptionError:
        return False

    return True


def _write_profile_for_sso(
        aws_profile,
        sso_start_url,
        sso_region,
        sso_account_id,
        region):
    config = configparser.ConfigParser()
    config.read(os.path.realpath(AWS_CONFIG_PATH))
    section = 'profile {}'.format(aws_profile)

    if section not in config.sections():
        config.add_section(section)
    config.set(section, 'sso_start_url', sso_start_url)
    config.set(section, 'sso_region', sso_region)
    config.set(section, 'sso_account_id', sso_account_id)
    config.set(section, 'sso_role_name', 'PowerUserAccessPlus')
    config.set(section, 'region', region)
    config.set(section, 'output', 'json')
    with open(AWS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        config.write(f)


def _has_valid_session_credentials_for_sso():
    for filepath in _iter_files_in_dir(AWS_SSO_CACHE_DIR):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                contents = json.load(f)
        except JSONDecodeError:
            continue

        if 'startUrl' in contents and 'expiresAt' in contents:
            expiration = parser.parse(contents['expiresAt'])
            return pytz.utc.localize(datetime.utcnow()) < expiration
    return False


def _refresh_sso_credentials(aws_session_profile):
    check_output(['aws', 'sso', 'login'], env={'AWS_PROFILE': aws_session_profile})


def _has_valid_v1_session_credentials(aws_profile):
    config = configparser.ConfigParser()
    config.read(os.path.realpath(AWS_CREDENTIALS_PATH))
    if aws_profile not in config.sections():
        return False
    try:
        expiration = parser.parse(config.get(aws_profile, 'expiration'))
    except configparser.NoOptionError:
        return False

    return pytz.utc.localize(datetime.utcnow()) < expiration


def _iter_files_in_dir(directory):
    """
    Yield each filepath under a directory path that corresponds to a file (not a dir)
    """
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            yield filepath


def _ensure_all_dirs(path, mode=0o700):
    if not os.path.exists(path):
        os.makedirs(path, mode=mode)
