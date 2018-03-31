import jsonobject


class _Constants(jsonobject.JsonObject):
    formplayer_db_name = jsonobject.StringProperty(default='formplayer')
    postgresql_db_name = jsonobject.StringProperty(default='commcarehq')


constants = _Constants()
