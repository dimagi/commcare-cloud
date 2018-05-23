import jsonobject

GitUriProperty = jsonobject.StringProperty
TimezoneProperty = jsonobject.StringProperty

class FabSettingsConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    sudo_user = jsonobject.StringProperty()
    default_branch = jsonobject.StringProperty()
    home = jsonobject.StringProperty()
    project = jsonobject.StringProperty()
    code_repo = GitUriProperty()
    timing_log = jsonobject.StringProperty()
    keepalive = jsonobject.IntegerProperty()
    ignore_kafka_checkpoint_warning = jsonobject.BooleanProperty()
    acceptable_maintenance_window = jsonobject.ObjectProperty(lambda: AcceptableMaintenanceWindow)
    email_enabled = jsonobject.BooleanProperty()


class AcceptableMaintenanceWindow(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    hour_start = jsonobject.IntegerProperty()
    hour_end = jsonobject.IntegerProperty()
    timezone = TimezoneProperty()
