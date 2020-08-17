from commcare_cloud.environment.secrets.secrets_schema import get_known_secret_specs


class AnsibleVaultSecretsBackend(object):
    def __init__(self):
        pass

    def get_generated_variables(self):
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
