import jsonobject


class ProxyConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    SITE_HOST = jsonobject.StringProperty(required=True)
    NO_WWW_SITE_HOST = jsonobject.StringProperty()
    J2ME_SITE_HOST = jsonobject.StringProperty()
    nginx_combined_cert_value = jsonobject.StringProperty()
    nginx_key_value = jsonobject.StringProperty()
    nginx_hsts_max_age = jsonobject.IntegerProperty()
    nginx_max_worker_connection = jsonobject.IntegerProperty(default=512)
    nginx_worker_rlimit_nofile = jsonobject.IntegerProperty()
    fake_ssl_cert = jsonobject.BooleanProperty(default=False)
    letsencrypt_cchq_ssl = jsonobject.BooleanProperty(default=False)
    letsencrypt_cas_ssl = jsonobject.BooleanProperty(default=False)
    primary_ssl_env = jsonobject.StringProperty()

    special_sites = jsonobject.ListProperty(str)

    COMMTRACK_SITE_HOST = jsonobject.StringProperty(exclude_if_none=True)
    commtrack_nginx_combined_cert_value = jsonobject.StringProperty(exclude_if_none=True)
    commtrack_key_value = jsonobject.StringProperty(exclude_if_none=True)

    CAS_SITE_HOST = jsonobject.StringProperty(exclude_if_none=True)
    cas_nginx_combined_cert_value = jsonobject.StringProperty(exclude_if_none=True)
    cas_key_value = jsonobject.StringProperty(exclude_if_none=True)

    REACH_SITE_HOST = jsonobject.StringProperty(exclude_if_none=True)

    TABLEAU_HOST = jsonobject.StringProperty(exclude_if_none=True)
    tableau_nginx_combined_cert_value = jsonobject.StringProperty(exclude_if_none=True)
    tableau_key_value = jsonobject.StringProperty(exclude_if_none=True)
    tableau_server = jsonobject.StringProperty(exclude_if_none=True)

    PNA_SITE_HOST = jsonobject.StringProperty(exclude_if_none=True)
    pna_nginx_combined_cert_value = jsonobject.StringProperty(exclude_if_none=True)
    pna_key_value = jsonobject.StringProperty(exclude_if_none=True)

    def check(self):
        pass

    def to_generated_variables(self):
        variables = self.to_json()
        if self.nginx_worker_rlimit_nofile is None:
            variables['nginx_worker_rlimit_nofile'] = "{{ nofile_limit }}"
        return variables

    @classmethod
    def get_claimed_variables(cls):
        return set(cls._properties_by_key.keys())
