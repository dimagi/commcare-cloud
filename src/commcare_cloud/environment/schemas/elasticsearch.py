import jsonobject


class ElasticsearchConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    settings = jsonobject.ObjectProperty(lambda: SettingsByIndexConfig)


def es_settings_property():
    return jsonobject.ObjectProperty(lambda: SettingsConfig)


class SettingsByIndexConfig(jsonobject.JsonObject):
    default = es_settings_property()
    case_search = es_settings_property()
    hqapps = es_settings_property()
    hqcases = es_settings_property()
    hqdomains = es_settings_property()
    hqgroups = es_settings_property()
    hqusers = es_settings_property()
    ledgers = es_settings_property()
    report_cases = es_settings_property()
    report_xforms = es_settings_property()
    smslogs = es_settings_property()
    xforms = es_settings_property()


class IntegerProperty(jsonobject.IntegerProperty):
    """
    Overriding jsonobject.IntegerProperty to improve exclude_if_none behavior

    Instead of treating 0 like "none", it only treats literal None as "none".
    """
    def exclude(self, value):
        return self.exclude_if_none and value is None


class SettingsConfig(jsonobject.JsonObject):
    number_of_shards = IntegerProperty(exclude_if_none=True)
    number_of_replicas = IntegerProperty(exclude_if_none=True)
