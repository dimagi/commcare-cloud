import jsonobject
from commcare_cloud.environment.paths import get_role_defaults


def get_defaults_jsonobject(role, **kwargs):
    """
    Create a JsonObject subclass that has a property for every default variable in :role:

    additionally, calling to_json() on an instance will exclude any variables
    that are set to the original default

    :param role: ansible role to look for defaults/main.yml file of.
            Must be under ansible/roles/.
    :param kwargs: extra properties to define explicitly.
            Useful if autodetection is not enough.
    :return: The new JsonObject subclass.
    """
    cls = type(jsonobject.JsonObject)(
        '{}_Defaults'.format(role), (jsonobject.JsonObject,),
        dict(get_role_defaults(role), _allow_dynamic_properties=False, **kwargs))

    # exclude from to_json if set to the default value
    def exclude(self, value):
        return value == self.default()

    for property_ in cls._properties_by_key.values():
        property_.exclude = exclude.__get__(property_)

    return cls
