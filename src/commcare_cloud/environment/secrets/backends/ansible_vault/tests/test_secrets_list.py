from __future__ import absolute_import
from __future__ import unicode_literals
import os

import yaml

from commcare_cloud.environment.secrets.backends.ansible_vault.main import AnsibleVaultSecretsBackend
from commcare_cloud.environment.secrets.utils import yaml_diff


def test_generated_variables_as_expected():
    with open(os.path.join(os.path.dirname(__file__), 'expected-generated-variables.yml')) as f:
        expected_generated_variables = yaml.safe_load(f)
    generated_variables = AnsibleVaultSecretsBackend('a', 'b').get_generated_variables()
    assert generated_variables == expected_generated_variables, \
        yaml_diff(generated_variables, expected_generated_variables)
