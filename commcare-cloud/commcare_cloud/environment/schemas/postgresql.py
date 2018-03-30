import jsonobject


class PostgresqlConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    postgresql_dbs = jsonobject.ListProperty(lambda: DBOptions, required=True)


class DBOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty(exclude_if_none=True)
    host = jsonobject.StringProperty(exclude_if_none=True)
    port = jsonobject.IntegerProperty(exclude_if_none=True)
    user = jsonobject.StringProperty(exclude_if_none=True)
    password = jsonobject.StringProperty(exclude_if_none=True)
    options = jsonobject.DictProperty(unicode, exclude_if_none=True)
    django_alias = jsonobject.StringProperty(exclude_if_none=True)
    shards = jsonobject.ListProperty(int, exclude_if_none=True)  # [start, end] pair
    django_migrate = jsonobject.BooleanProperty(exclude_if_none=True)
    query_stats = jsonobject.BooleanProperty(exclude_if_none=True)
    create = jsonobject.BooleanProperty(exclude_if_none=True)
