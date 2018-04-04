import jsonobject


class PostgresqlConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    SEPARATE_SYNCLOGS_DB = jsonobject.BooleanProperty(default=True)
    DEFAULT_POSTGRESQL_HOST = jsonobject.StringProperty(default=None)
    DEFAULT_POSTGRESQL_USER = jsonobject.StringProperty(default="{{ secrets.POSTGRES_USERS.commcare.username }}")
    DEFAULT_POSTGRESQL_PASSWORD = jsonobject.StringProperty(default="{{ secrets.POSTGRES_USERS.commcare.password }}")
    REPORTING_DATABASES = jsonobject.DictProperty(default=lambda: {"ucr": "ucr"})

    postgresql_dbs = jsonobject.ListProperty(lambda: DBOptions, required=True)

    @classmethod
    def wrap(cls, data):
        self = super(PostgresqlConfig, cls).wrap(data)
        for db in self.postgresql_dbs:
            if not db.user:
                db.user = self.DEFAULT_POSTGRESQL_USER
            if not db.password:
                db.password = self.DEFAULT_POSTGRESQL_PASSWORD
        return self

    def replace_hosts(self, environment):
        if self.DEFAULT_POSTGRESQL_HOST is None:
            self.DEFAULT_POSTGRESQL_HOST = environment.groups['postgresql'][0]
        elif self.DEFAULT_POSTGRESQL_HOST != '127.0.0.1':
            self.DEFAULT_POSTGRESQL_HOST = environment.translate_host(
                self.DEFAULT_POSTGRESQL_HOST, environment.paths.postgresql_yml)

        for db in self.postgresql_dbs:
            if db.host is None:
                db.host = self.DEFAULT_POSTGRESQL_HOST
            elif db.host != '127.0.0.1':
                db.host = environment.translate_host(db.host, environment.paths.postgresql_yml)


class DBOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty(required=True)
    host = jsonobject.StringProperty()
    port = jsonobject.IntegerProperty(default=6432)
    user = jsonobject.StringProperty()
    password = jsonobject.StringProperty()
    options = jsonobject.DictProperty(unicode)
    django_alias = jsonobject.StringProperty()
    shards = jsonobject.ListProperty(int, exclude_if_none=True)  # [start, end] pair
    django_migrate = jsonobject.BooleanProperty(default=True)
    query_stats = jsonobject.BooleanProperty(default=False)
    create = jsonobject.BooleanProperty(default=True)
