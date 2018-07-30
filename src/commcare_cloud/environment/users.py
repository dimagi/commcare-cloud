from __future__ import absolute_import
import jsonobject
import six


class UsersConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    dev_users = jsonobject.ObjectProperty(lambda: DevUsers)


class DevUsers(jsonobject.JsonObject):
    present = jsonobject.ListProperty(six.text_type)
    absent = jsonobject.ListProperty(six.text_type)
