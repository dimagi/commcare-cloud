import jsonobject


class UsersConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    dev_users = jsonobject.ObjectProperty(lambda: DevUsers)


class DevUsers(jsonobject.JsonObject):
    present = jsonobject.ListProperty(unicode)
    absent = jsonobject.ListProperty(unicode)
