import os

import jsonobject
import yaml

from commcare_cloud.environment.paths import PACKAGE_BASE


class SecretSpec(jsonobject.JsonObject):
    name = jsonobject.StringProperty(required=True)
    required = jsonobject.BooleanProperty(default=False)
    default = jsonobject.DefaultProperty(default=None)
    default_overrides_falsy_values = jsonobject.BooleanProperty(default=False)
    fall_back_to_vars = jsonobject.ListProperty(str)
    deprecated = jsonobject.BooleanProperty(default=False)
    legacy_namespace = jsonobject.StringProperty(choices=('localsettings_private', 'secrets', None))
    ansible_var_lowercase = jsonobject.BooleanProperty(default=False)

    @classmethod
    def wrap(cls, data):
        self = super(SecretSpec, cls).wrap(data)
        if self.required:
            assert self.default is None, "A required secret cannot also have a default."
        return self

    def get_legacy_reference(self):
        if self.legacy_namespace:
            return "{}.{}".format(self.legacy_namespace, self.name)
        else:
            return self.name


def get_known_secret_specs():
    with open(os.path.join(PACKAGE_BASE, 'environment', 'secrets', 'secrets.yml')) as f:
        return [SecretSpec.wrap(secret_spec) for secret_spec in yaml.safe_load(f)]


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
        if expression != secret_spec.name:  # avoid redundant `x: {{ x }}`
            generated_variables[ansible_var_name] = "{{{{ {} }}}}".format(expression)
    return generated_variables
