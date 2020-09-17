from __future__ import absolute_import
import os

import jsonobject
import yaml
from memoized import memoized

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

    def get_ansible_var_name(self):
        if self.ansible_var_lowercase:
            return self.name.lower()
        else:
            return self.name

    def get_ansible_expression(self, expression_base_function, other_secret_specs_by_name):
        expression = expression_base_function(self)
        for var_name in self.fall_back_to_vars:
            expression += ' | default({})'.format(other_secret_specs_by_name[var_name].get_ansible_var_name())
        if not self.required:
            if self.default_overrides_falsy_values:
                expression += ' | default({}, true)'.format(repr(self.default).strip('u'))
            else:
                expression += ' | default({})'.format(repr(self.default).strip('u'))
        if expression == self.name:
            # avoid redundant/cyclical `x: {{ x }}`
            return None
        else:
            return "{{{{ {} }}}}".format(expression)


def get_known_secret_specs():
    with open(os.path.join(PACKAGE_BASE, 'environment', 'secrets', 'secrets.yml')) as f:
        return [SecretSpec.wrap(secret_spec) for secret_spec in yaml.safe_load(f)]


@memoized
def get_known_secret_specs_by_name():
    return {secret_spec.name: secret_spec for secret_spec in get_known_secret_specs()}


def get_generated_variables(expression_base_function):
    """
    expression_base_function is a function that takes in a secret_spec
    and returns an expression for fetching the value

    This function then returns something like
    {'VAR_NAME': '{{ <base expression to fetch VAR_NAME> | default(None) }}', ...}
    based on the parameters of each secret_spec.

    expression_base_function is passed in like this because the base expression for fetching
    the value of the secret in ansible tends to change with different secrets backends,
    whereas the logic for the rest of each expression does not.
    """
    secret_specs_by_name = get_known_secret_specs_by_name()
    generated_variables = {}
    for secret_spec in secret_specs_by_name.values():
        ansible_expression = secret_spec.get_ansible_expression(
            expression_base_function=expression_base_function,
            other_secret_specs_by_name=secret_specs_by_name,
        )
        if ansible_expression:
            generated_variables[secret_spec.get_ansible_var_name()] = ansible_expression
    return generated_variables
