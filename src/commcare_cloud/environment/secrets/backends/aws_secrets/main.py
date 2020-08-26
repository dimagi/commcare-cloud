import json

import boto3
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
        return AwsSecretsBackend(secret_name_prefix='commcare-{}'.format(environment.name), environment=environment)

    def get_generated_variables(self):
        return get_generated_variables(
            lambda secret_spec: "lookup('aws_secret', '{}/{}')".format(self.secret_name_prefix, secret_spec.name))

    def get_extra_ansible_env_vars(self):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        aws_profile = aws_sign_in(self.environment)
        env_vars = {
            'AWS_REGION': self.environment.terraform_config.region,
        }
        if aws_profile:
            env_vars.update({'AWS_PROFILE': aws_profile})
        return env_vars

    def get_secret(self, var):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        return json.loads(
            boto3.session.Session(profile_name=aws_sign_in(self.environment)).client(
                'secretsmanager', region_name=self.environment.terraform_config.region
            )
            .get_secret_value(SecretId='commcare-{}/{}'.format(self.environment.name, var))['SecretString']
        )

    def set_secret(self, var, value):
        value = json.dumps(value)
        try:
            self._secrets_client.put_secret_value(
                SecretId='commcare-{}/{}'.format(self.environment.name, var),
                SecretString=value,
            )
        except self._secrets_client.exceptions.ResourceNotFoundException:
            self._secrets_client.create_secret(
                Name='commcare-{}/{}'.format(self.environment.name, var),
                SecretString=value,
            )

    @memoized_property
    def _secrets_client(self):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        return boto3.session.Session(profile_name=aws_sign_in(self.environment)).client(
            'secretsmanager', region_name=self.environment.terraform_config.region
        )
