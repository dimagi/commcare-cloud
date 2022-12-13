import jsonobject

from commcare_cloud.environment.secrets.backends import all_secrets_backends_by_name


class MetaConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    deploy_env = jsonobject.StringProperty(required=True)
    always_deploy_formplayer = jsonobject.BooleanProperty(default=False)
    env_monitoring_id = jsonobject.StringProperty(required=True)
    users = jsonobject.ListProperty(str, required=True)
    slack_alerts_channel = jsonobject.StringProperty()
    slack_notifications_channel = jsonobject.StringProperty()
    bare_non_cchq_environment = jsonobject.BooleanProperty(default=False)
    deploy_keys = jsonobject.DictProperty(str)
    secrets_backend = jsonobject.StringProperty(
        choices=list(all_secrets_backends_by_name),
        default='ansible-vault',
    )

    def get_secrets_backend_class(self):
        # guaranteed to succeed because of the validation above on secrets_backend
        return all_secrets_backends_by_name[self.secrets_backend]
