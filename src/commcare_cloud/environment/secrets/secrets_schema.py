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
