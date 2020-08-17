import difflib
import os

import yaml

from commcare_cloud.environment.secrets.backends.ansible_vault.main import AnsibleVaultSecretsBackend


def test_generated_variables_as_expected():
    with open(os.path.join(os.path.dirname(__file__), 'expected-generated-variables.yml')) as f:
        expected_generated_variables = yaml.safe_load(f)
    generated_variables = AnsibleVaultSecretsBackend().get_generated_variables()
    assert generated_variables == expected_generated_variables, \
        yaml_diff(generated_variables, expected_generated_variables)


def yaml_diff(obj_1, obj_2):
    yaml_lines_1 = yaml.safe_dump(obj_1, width=1000).splitlines()
    yaml_lines_2 = yaml.safe_dump(obj_2, width=1000).splitlines()
    return '\n'.join(list(difflib.ndiff(yaml_lines_1, yaml_lines_2)))
