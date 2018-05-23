import jsonobject


class MetaConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    deploy_env = jsonobject.StringProperty(required=True)
    env_monitoring_id = jsonobject.StringProperty(required=True)
    users = jsonobject.StringProperty(required=True)
    slack_alerts_channel = jsonobject.StringProperty()
