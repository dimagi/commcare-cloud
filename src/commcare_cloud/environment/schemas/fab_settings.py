import jsonobject

from commcare_cloud.colors import color_notice, color_code

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
    tag_deploy_commits = jsonobject.BooleanProperty(default=False)
    shared_dir_for_staticfiles = jsonobject.StringProperty(default=None)
    deploy_event_url = jsonobject.StringProperty(default=None)
    generate_deploy_diffs = jsonobject.BooleanProperty(default=True)
    custom_deploy_details = jsonobject.DictProperty()

    @classmethod
    def wrap(cls, data):
        for deprecated_property in ('py3_include_venv', 'py3_run_deploy'):
            if deprecated_property in data:
                print("{} {} {}".format(
                    color_notice("The property"),
                    color_code(deprecated_property),
                    color_notice("is deprecated and has no effect.")
                ))
                print(color_notice("Feel free to remove it from your fab-settings.yml."))
                del data[deprecated_property]

        if not data.pop("use_shared_dir_for_staticfiles", True):
            data.pop("shared_dir_for_staticfiles", None)

        return super(FabSettingsConfig, cls).wrap(data)


class AcceptableMaintenanceWindow(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    hour_start = jsonobject.IntegerProperty()
    hour_end = jsonobject.IntegerProperty()
    timezone = TimezoneProperty()
