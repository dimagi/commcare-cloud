import boto3

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
        return {'AWS_REGION': self.environment.terraform_config.region}

    def get_secret(self, var):
        from commcare_cloud.commands.terraform.aws import aws_sign_in
        return (
            boto3.session.Session(profile_name=aws_sign_in(self.environment)).client(
                'secretsmanager', region_name=self.environment.terraform_config.region
            )
            .get_secret_value(SecretId='commcare-{}/{}'.format(self.environment.name, var))['SecretString']
        )

    def set_secret(self, var, value):
        raise NotImplementedError
