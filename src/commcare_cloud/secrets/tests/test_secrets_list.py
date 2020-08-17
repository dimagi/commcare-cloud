import difflib
import os

import yaml

from commcare_cloud.secrets.secrets_schema import get_known_secret_specs


def test_generated_variables_as_expected():
    with open(os.path.join(os.path.dirname(__file__), 'expected-generated-variables.yml')) as f:
        expected_generated_variables = yaml.safe_load(f)
    assert get_generated_variables() == expected_generated_variables, \
        yaml_diff(get_generated_variables(), expected_generated_variables)


def get_generated_variables():
    secret_specs = get_known_secret_specs()
    secret_specs_by_name = {secret_spec.name: secret_spec for secret_spec in secret_specs}
    generated_variables = {}
    for secret_spec in secret_specs:
        if secret_spec.ansible_var_lowercase:
            ansible_var_name = secret_spec.name.lower()
        else:
            ansible_var_name = secret_spec.name
        expression = secret_spec.get_legacy_reference()
        for var_name in secret_spec.fall_back_to_vars:
            expression += ' | default({})'.format(secret_specs_by_name[var_name].get_legacy_reference())
        if not secret_spec.required:
            if secret_spec.default_overrides_falsy_values:
                expression += ' | default({}, true)'.format(repr(secret_spec.default).strip('u'))
            else:
                expression += ' | default({})'.format(repr(secret_spec.default).strip('u'))
        generated_variables[ansible_var_name] = "{{{{ {} }}}}".format(expression)
    return generated_variables


def yaml_diff(obj_1, obj_2):
    yaml_lines_1 = yaml.safe_dump(obj_1, width=1000).splitlines()
    yaml_lines_2 = yaml.safe_dump(obj_2, width=1000).splitlines()
    return '\n'.join(list(difflib.ndiff(yaml_lines_1, yaml_lines_2)))
