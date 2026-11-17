import jsonobject


class AwsConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    credential_style = jsonobject.StringProperty(choices=('sso', 'iam'), default='iam')
    sso_config = jsonobject.ObjectProperty(lambda: SsoConfig, default=None)
    ses_config = jsonobject.ObjectProperty(lambda: SesConfig, default=None)


class SsoConfig(jsonobject.JsonObject):
    sso_start_url = jsonobject.StringProperty()
    sso_region = jsonobject.StringProperty()
    sso_account_id = jsonobject.StringProperty()
    region = jsonobject.StringProperty()


class SesConfig(jsonobject.JsonObject):
    iam_username = jsonobject.StringProperty()
    account_id = jsonobject.StringProperty()
    role_name = jsonobject.StringProperty()
    region = jsonobject.StringProperty()
