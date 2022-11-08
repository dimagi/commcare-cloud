from __future__ import absolute_import
from __future__ import unicode_literals
import json
import os
import shlex
import sys

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from memoized import memoized_property

from commcare_cloud.environment.secrets.backends.abstract_backend import AbstractSecretsBackend
from commcare_cloud.environment.secrets.secrets_schema import get_generated_variables
from commcare_cloud.commands.ansible.helpers import get_default_ssh_options_as_cmd_parts


class AwsSecretsBackend(AbstractSecretsBackend):
    name = 'aws-secrets'

    def __init__(self, secret_name_prefix, environment):
        self.secret_name_prefix = secret_name_prefix
        self.environment = environment
        self._validate_ssm_proxy()

    def _validate_ssm_proxy(self):
        if (
            os.environ.get("COMMCARE_CLOUD_PROXY_SSM")
            and not self.environment.public_vars.get("allow_aws_ssm_proxy")
        ):
            sys.exit(
                "ERROR: AWS SSM proxy is not allowed for this environment. "
                "Use --control and/or unset COMMCARE_CLOUD_PROXY_SSM instead."
            )

    @classmethod
    def from_environment(cls, environment):
        return AwsSecretsBackend(
            secret_name_prefix='commcare-{}'.format(environment.name),
            environment=environment,
        )

    def prompt_user_input(self):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        # make sure this happens upfront and not lazily
        # Often there will be no prompt at all, but the first time you run it in a while
        # it'll trigger the AWS SSO process to refresh the temporary credentials
        aws_sign_in(self.environment)

    def get_generated_variables(self):
        # cchq_aws_secrets (unlike the built-in aws_secrets) assumes json encoded values
        # and json decodes them for the caller.
        # It's less elegant than doing it outside, but simplifies the error handling.
        return get_generated_variables(
            lambda secret_spec: "lookup('cchq_aws_secret', '{}/{}', errors='ignore')".format(
                self.secret_name_prefix, secret_spec.name))

    def has_extra_env_vars(self):
        return os.environ.get("COMMCARE_CLOUD_PROXY_SSM")

    def get_extra_ansible_env_vars(self):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        aws_profile = aws_sign_in(self.environment)
        env_vars = {
            'AWS_REGION': self.environment.terraform_config.region,
            # generate one-time use encryption key
            # for caching the secrets of this run to a file
            'AWS_SECRETS_CACHE_KEY': Fernet.generate_key()
        }
        if aws_profile:
            env_vars.update({'AWS_PROFILE': aws_profile})
            if os.environ.get("COMMCARE_CLOUD_PROXY_SSM"):
                env_vars['ANSIBLE_SSH_EXTRA_ARGS'] = _opt_str(self._get_ssm_args())
        if sys.platform == 'darwin':
            # Needed to get the ansible aws_secrets lookup plugin to work on MacOS
            # More on the underlying ansible issue: https://github.com/ansible/ansible/issues/49207
            env_vars.update({'OBJC_DISABLE_INITIALIZE_FORK_SAFETY': 'YES'})
        return env_vars

    def _get_ssm_args(self):
        """Get SSH arguments to connect via AWS SSM with 'control' as jump host

        These options can be observed and debugged with environment variables:

            ANSIBLE_VERBOSITY=3
            VERBOSE_TO_STDERR=true
        """
        from commcare_cloud.commands.inventory_lookup.getinventory import (
            HostMatchException,
            get_server_address,
        )
        try:
            control_ip = get_server_address(self.environment.name, 'control')
        except HostMatchException:
            print("cannot find {} 'control' machine".format(self.environment.name), file=sys.stderr)
            return []
        hostvars = self.environment.get_host_vars(control_ip)
        try:
            control_id = hostvars['ec2_instance_id']
        except KeyError:
            print("{} 'control' machine has no 'ec2_instance_id'".format(self.environment.name), file=sys.stderr)
            return []
        ssm_proxy = get_default_ssh_options_as_cmd_parts(self.environment, aws_ssm_target=control_id)
        return ['-o', 'ProxyCommand=' + _opt_str(['ssh', '-W', "%h:%p"] + ssm_proxy + [control_ip])]

    def _get_secret(self, var):
        try:
            return json.loads(
                self._secrets_client.get_secret_value(
                    SecretId='{}/{}'.format(self.secret_name_prefix, var))['SecretString']
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise

    def _set_secret(self, var, value):

        value = json.dumps(value)
        try:
            self._secrets_client.put_secret_value(
                SecretId='{}/{}'.format(self.secret_name_prefix, var),
                SecretString=value,
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self._secrets_client.create_secret(
                    Name='{}/{}'.format(self.secret_name_prefix, var),
                    SecretString=value,
                )
            else:
                raise

    @memoized_property
    def _secrets_client(self):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        return boto3.session.Session(profile_name=aws_sign_in(self.environment)).client(
            'secretsmanager', region_name=self.environment.terraform_config.region
        )


def _opt_str(args):
    return ' '.join(map(shlex.quote, args))
