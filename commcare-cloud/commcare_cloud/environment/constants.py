import jsonobject


class _Constants(jsonobject.JsonObject):
    formplayer_db_name = jsonobject.StringProperty(default='formplayer')


constants = _Constants()
