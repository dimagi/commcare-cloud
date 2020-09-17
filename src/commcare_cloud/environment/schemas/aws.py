from __future__ import absolute_import
import jsonobject


class AwsConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    credential_style = jsonobject.StringProperty(choices=('sso', 'iam'), default='iam')
    sso_config = jsonobject.ObjectProperty(lambda: SsoConfig, default=None)


class SsoConfig(jsonobject.JsonObject):
    sso_start_url = jsonobject.StringProperty()
    sso_region = jsonobject.StringProperty()
    sso_account_id = jsonobject.StringProperty()
    region = jsonobject.StringProperty()
