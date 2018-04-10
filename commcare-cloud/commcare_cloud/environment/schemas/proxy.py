import jsonobject


class ProxyConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    def check(self):
        pass
