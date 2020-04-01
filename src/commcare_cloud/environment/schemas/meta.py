from __future__ import absolute_import
import jsonobject
import six


class MetaConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    deploy_env = jsonobject.StringProperty(required=True)
    env_monitoring_id = jsonobject.StringProperty(required=True)
    users = jsonobject.ListProperty(six.text_type, required=True)
    slack_alerts_channel = jsonobject.StringProperty()
    bare_non_cchq_environment = jsonobject.BooleanProperty(default=False)
