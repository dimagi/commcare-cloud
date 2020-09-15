import os

import yaml

from commcare_cloud.environment.secrets.backends.aws_secrets.main import AwsSecretsBackend
from commcare_cloud.environment.secrets.utils import yaml_diff


def test_generated_variables_as_expected():
    with open(os.path.join(os.path.dirname(__file__), 'expected-generated-variables.yml')) as f:
        expected_generated_variables = yaml.safe_load(f)
    generated_variables = AwsSecretsBackend('commcare-staging', environment=None).get_generated_variables()
    assert generated_variables == expected_generated_variables, \
        yaml_diff(generated_variables, expected_generated_variables)
