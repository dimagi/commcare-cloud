import jsonobject


class PostgresqlConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    DEFAULT_POSTGRESQL_HOST = jsonobject.StringProperty(default="{{ groups.postgresql.0 }}")
    DEFAULT_POSTGRESQL_USER = jsonobject.StringProperty(default="{{ secrets.POSTGRES_USERS.commcare.username }}")
    DEFAULT_POSTGRESQL_PASSWORD = jsonobject.StringProperty(default="{{ secrets.POSTGRES_USERS.commcare.password }}")

    postgresql_dbs = jsonobject.ListProperty(lambda: DBOptions, required=True)

    @classmethod
    def wrap(cls, data):
        self = super(PostgresqlConfig, cls).wrap(data)
        for db in self.postgresql_dbs:
            if not db.host:
                db.host = self.DEFAULT_POSTGRESQL_HOST
            if not db.user:
                db.user = self.DEFAULT_POSTGRESQL_USER
            if not db.password:
                db.password = self.DEFAULT_POSTGRESQL_PASSWORD
        return self


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
    query_stats = jsonobject.BooleanProperty(exclude_if_none=True)
    create = jsonobject.BooleanProperty(default=True)
