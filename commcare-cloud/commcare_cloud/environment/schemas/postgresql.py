import jsonobject


class PostgresqlConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    DEFAULT_POSTGRESQL_HOST = jsonobject.StringProperty(default="{{ groups.postgresql.0 }}")
    postgresql_dbs = jsonobject.ListProperty(lambda: DBOptions, required=True)

    @classmethod
    def wrap(cls, data):
        self = super(PostgresqlConfig, cls).wrap(data)
        for db in self.postgresql_dbs:
            if not db.host:
                db.host = self.DEFAULT_POSTGRESQL_HOST
        return self


class DBOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty(exclude_if_none=True)
    host = jsonobject.StringProperty()
    port = jsonobject.IntegerProperty(default=6432)
    user = jsonobject.StringProperty(exclude_if_none=True)
    password = jsonobject.StringProperty(exclude_if_none=True)
    options = jsonobject.DictProperty(unicode, exclude_if_none=True)
    django_alias = jsonobject.StringProperty(exclude_if_none=True)
    shards = jsonobject.ListProperty(int, exclude_if_none=True)  # [start, end] pair
    django_migrate = jsonobject.BooleanProperty(default=True)
    query_stats = jsonobject.BooleanProperty(exclude_if_none=True)
    create = jsonobject.BooleanProperty(exclude_if_none=True)
