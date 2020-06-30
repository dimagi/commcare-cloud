import jsonobject


class GitRepository(jsonobject.JsonObject):
    url = jsonobject.StringProperty(required=True)
    dest = jsonobject.StringProperty(default="")  # relative to the release directory
    version = jsonobject.StringProperty(default="master")
    requirements_path = jsonobject.StringProperty(default="requirements.txt")


class MetaConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    deploy_env = jsonobject.StringProperty(required=True)
    always_deploy_formplayer = jsonobject.BooleanProperty(default=False)
    env_monitoring_id = jsonobject.StringProperty(required=True)
    users = jsonobject.ListProperty(unicode, required=True)
    slack_alerts_channel = jsonobject.StringProperty()
    bare_non_cchq_environment = jsonobject.BooleanProperty(default=False)
    git_repositories = jsonobject.ListProperty(GitRepository)
