import json
import sys

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from memoized import memoized_property

from commcare_cloud.environment.secrets.backends.abstract_backend import AbstractSecretsBackend
from commcare_cloud.environment.secrets.secrets_schema import get_generated_variables


class AwsSecretsBackend(AbstractSecretsBackend):
    name = 'aws-secrets'

    def __init__(self, secret_name_prefix, environment):
        self.secret_name_prefix = secret_name_prefix
        self.environment = environment

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
        if sys.platform == 'darwin':
            # Needed to get the ansible aws_secrets lookup plugin to work on MacOS
            # More on the underlying ansible issue: https://github.com/ansible/ansible/issues/49207
            env_vars.update({'OBJC_DISABLE_INITIALIZE_FORK_SAFETY': 'YES'})
        return env_vars

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
