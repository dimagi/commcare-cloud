import jsonobject
import re

from commcare_cloud.environment.constants import constants


class PostgresqlConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    SEPARATE_SYNCLOGS_DB = jsonobject.BooleanProperty(default=True)
    DEFAULT_POSTGRESQL_HOST = jsonobject.StringProperty(default=None)
    DEFAULT_POSTGRESQL_USER = jsonobject.StringProperty(default="{{ secrets.POSTGRES_USERS.commcare.username }}")
    DEFAULT_POSTGRESQL_PASSWORD = jsonobject.StringProperty(default="{{ secrets.POSTGRES_USERS.commcare.password }}")
    REPORTING_DATABASES = jsonobject.DictProperty(default=lambda: {"ucr": "ucr"})

    postgresql_dbs = jsonobject.ListProperty(lambda: ShardDBOptions, required=True)
    dbs = jsonobject.ObjectProperty(lambda: SmartDBConfig, required=True)

    @property
    def all_dbs(self):
        return self.postgresql_dbs + self.generate_postgresql_dbs()

    @classmethod
    def wrap(cls, data):
        self = super(PostgresqlConfig, cls).wrap(data)
        for db in self.all_dbs:
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

        for db in self.all_dbs:
            if db.host is None:
                db.host = self.DEFAULT_POSTGRESQL_HOST
            elif db.host != '127.0.0.1':
                db.host = environment.translate_host(db.host, environment.paths.postgresql_yml)

    def generate_postgresql_dbs(self):
        return [self.dbs.main] + self.dbs.custom

    def check(self):
        def get_normalized(db_list):
            return sorted([db.to_json() for db in db_list], key=lambda db: db['name'])

        assert get_normalized(self.generate_postgresql_dbs()) == \
            get_normalized(self.postgresql_dbs), \
            "{} != {}".format(get_normalized(self.generate_postgresql_dbs()),
                              get_normalized(self.postgresql_dbs))


class SmartDBConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    main = jsonobject.ObjectProperty(lambda: MainDBOptions)

    custom = jsonobject.ListProperty(lambda: ShardDBOptions)


class DBOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty(required=True)
    host = jsonobject.StringProperty()
    port = jsonobject.IntegerProperty(default=6432)
    user = jsonobject.StringProperty()
    password = jsonobject.StringProperty()
    options = jsonobject.DictProperty(unicode)
    django_alias = jsonobject.StringProperty()
    django_migrate = jsonobject.BooleanProperty(default=True)
    query_stats = jsonobject.BooleanProperty(default=False)
    create = jsonobject.BooleanProperty(default=True)

    @classmethod
    def wrap(cls, data):
        self = super(DBOptions, cls).wrap(data)
        if re.match('^{{\s*commcarehq_main_db_name\s*}}$', self.name):
            self.name = constants.commcarehq_main_db_name
        return self


class MainDBOptions(DBOptions):
    name = constants.commcarehq_main_db_name
    django_alias = 'default'


class ShardDBOptions(DBOptions):
    shards = jsonobject.ListProperty(int, exclude_if_none=True)  # [start, end] pair
