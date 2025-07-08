from __future__ import absolute_import
import jsonobject


class UsersConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    dev_users = jsonobject.ObjectProperty(lambda: DevUsers)


class DevUsers(jsonobject.JsonObject):
    present = jsonobject.ListProperty(str)
    absent = jsonobject.ListProperty(str)
