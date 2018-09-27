import jsonobject
import re

import six

from commcare_cloud.environment.constants import constants
from commcare_cloud.environment.schemas.role_defaults import get_defaults_jsonobject

PostgresqlOverride = get_defaults_jsonobject(
    'postgresql',
    allow_dump_from_pgstandby=jsonobject.BooleanProperty,
)


def alphanum_key(key):
    """
    Used to generate a natural numeric sort key

    Example: ("p10" => ["p", 10]) is greater than ("p1" => ["p", 1])

    adapted from https://stackoverflow.com/a/2669120/240553
    """
    def convert(text):
        return int(text) if text.isdigit() else text
    return [convert(c) for c in re.split(r'([0-9]+)', key)]


def _is_power_of_2(num):
    return num and not (num & (num - 1))


def validate_shards(shard_ranges_by_partition_name):
    """
    Validate that shards partitioning in config is valid

    based off of
    https://github.com/dimagi/commcare-hq/blob/d8fdc0e5b2f7a3200ea743da60be8f808ddd8a60/corehq/sql_db/config.py#L74-L93

    """
    shards_seen = set()
    previous_range = None
    for group, shard_range, in sorted(list(shard_ranges_by_partition_name.items()),
                                      key=lambda x: x[1]):
        if not previous_range:
            assert shard_range[0] == 0, 'Shard numbering must start at 0'
        else:
            assert previous_range[1] + 1 == shard_range[0], \
                'Shards must be numbered consecutively: {} -> {}'.format(
                    previous_range[1], shard_range[0])

        shards_seen |= set(range(shard_range[0], shard_range[1] + 1))
        previous_range = shard_range

    num_shards = len(shards_seen)

    assert _is_power_of_2(num_shards), \
        'Total number of shards must be a power of 2: {}'.format(num_shards)


DEFAULT_POSTGRESQL_USER = "{{ secrets.POSTGRES_USERS.commcare.username }}"
DEFAULT_POSTGRESQL_PASSWORD = "{{ secrets.POSTGRES_USERS.commcare.password }}"
DEFAULT_PORT = 6432


class PostgresqlConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    SEPARATE_SYNCLOGS_DB = jsonobject.BooleanProperty(default=True)
    SEPARATE_FORM_PROCESSING_DBS = jsonobject.BooleanProperty(default=True)
    DEFAULT_POSTGRESQL_HOST = jsonobject.StringProperty(default=None)
    REPORTING_DATABASES = jsonobject.DictProperty(default=lambda: {"ucr": "ucr"})
    LOAD_BALANCED_APPS = jsonobject.DictProperty(default={})
    host_settings = jsonobject.DictProperty(lambda: HostSettings)
    dbs = jsonobject.ObjectProperty(lambda: SmartDBConfig)

    override = jsonobject.ObjectProperty(PostgresqlOverride)

    @classmethod
    def wrap(cls, data):
        # for better validation error message
        PostgresqlOverride.wrap(data.get('override', {}))
        self = super(PostgresqlConfig, cls).wrap(data)
        for db in self.generate_postgresql_dbs():
            if not db.user:
                db.user = DEFAULT_POSTGRESQL_USER
            if not db.password:
                db.password = DEFAULT_POSTGRESQL_PASSWORD
        return self

    def to_generated_variables(self):
        data = self.to_json()
        del data['override']
        data['postgresql_dbs'] = data.pop('dbs')
        data['postgresql_dbs']['all'] = sorted(
            (db.to_json() for db in self.generate_postgresql_dbs()),
            key=lambda db: db['name']
        )
        data.update(self.override.to_json())
        return data

    def replace_hosts(self, environment):
        if self.DEFAULT_POSTGRESQL_HOST is None:
            self.DEFAULT_POSTGRESQL_HOST = environment.groups['postgresql'][0]
        elif self.DEFAULT_POSTGRESQL_HOST != '127.0.0.1':
            self.DEFAULT_POSTGRESQL_HOST = environment.translate_host(
                self.DEFAULT_POSTGRESQL_HOST, environment.paths.postgresql_yml)

        host_settings = {
            environment.translate_host(host, environment.paths.postgresql_yml): value
            for host, value in self.host_settings.items()
        }

        for db in self.generate_postgresql_dbs():
            if db.host is None:
                db.host = self.DEFAULT_POSTGRESQL_HOST
            elif db.host != '127.0.0.1':
                db.host = environment.translate_host(db.host, environment.paths.postgresql_yml)
            if db.port is None:
                if db.host in host_settings:
                    db.port = host_settings[db.host].port
                else:
                    db.port = DEFAULT_PORT

    def generate_postgresql_dbs(self):
        return filter(None, [
            self.dbs.main, self.dbs.synclogs,
        ] + (
            self.dbs.form_processing.get_db_list() if self.dbs.form_processing else []
        ) + [self.dbs.ucr, self.dbs.formplayer] + self.dbs.custom + self.dbs.standby)

    def _check_reporting_databases(self):
        referenced_django_aliases = set()
        defined_django_aliases = {db.django_alias for db in self.generate_postgresql_dbs()
                                  if db.django_alias is not None}
        for reporting_alias, value in self.REPORTING_DATABASES.items():
            if isinstance(value, six.string_types):
                referenced_django_aliases.add(value)
            else:
                # value is {WRITE: alias, READ: [(alias, weight)...]}
                referenced_django_aliases.add(value['WRITE'])
                for alias, _ in value['READ']:
                    referenced_django_aliases.add(alias)
        assert referenced_django_aliases - defined_django_aliases == set(), \
            ("REPORTING_DATABASES must refer only to defined django aliases: {} not in {}"
             .format(', '.join(sorted(referenced_django_aliases - defined_django_aliases)),
                     ', '.join(sorted(defined_django_aliases))))

    def _check_shards(self):
        if self.dbs.form_processing:
            validate_shards({name: db.shards
                             for name, db in self.dbs.form_processing.partitions.items()})

    def check(self):
        self._check_reporting_databases()
        self._check_shards()
        assert (self.SEPARATE_SYNCLOGS_DB if self.dbs.synclogs is not None
                else not self.SEPARATE_SYNCLOGS_DB), \
            'synclogs should be None if and only if SEPARATE_SYNCLOGS_DB is False'
        assert (self.SEPARATE_FORM_PROCESSING_DBS if self.dbs.form_processing is not None
                else not self.SEPARATE_FORM_PROCESSING_DBS), \
            'form_processing should be None if and only if SEPARATE_FORM_PROCESSING_DBS is False'


class HostSettings(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    port = jsonobject.IntegerProperty(DEFAULT_PORT)


class SmartDBConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    main = jsonobject.ObjectProperty(lambda: MainDBOptions, required=True)
    formplayer = jsonobject.ObjectProperty(lambda: FormplayerDBOptions, required=True)
    ucr = jsonobject.ObjectProperty(lambda: UcrDBOptions, required=True)
    synclogs = jsonobject.ObjectProperty(lambda: SynclogsDBOptions, required=False)
    form_processing = jsonobject.ObjectProperty(lambda: FormProcessingConfig, required=False)
    phone_logs = jsonobject.ObjectProperty(lambda: PhonelogsDBOptions, required=False)

    custom = jsonobject.ListProperty(lambda: CustomDBOptions)
    standby = jsonobject.ListProperty(lambda: StandbyDBOptions)


class DBOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty(required=True)
    host = jsonobject.StringProperty()
    port = jsonobject.IntegerProperty(default=None)
    user = jsonobject.StringProperty()
    password = jsonobject.StringProperty()
    options = jsonobject.DictProperty(unicode)
    django_alias = jsonobject.StringProperty()
    django_migrate = jsonobject.BooleanProperty(default=True)
    query_stats = jsonobject.BooleanProperty(default=False)
    create = jsonobject.BooleanProperty(default=True)


class MainDBOptions(DBOptions):
    name = constants.commcarehq_main_db_name
    django_alias = 'default'


class FormplayerDBOptions(DBOptions):
    name = constants.formplayer_db_name
    django_alias = None


class UcrDBOptions(DBOptions):
    name = constants.ucr_db_name
    django_alias = 'ucr'
    django_migrate = False


class SynclogsDBOptions(DBOptions):
    name = constants.synclogs_db_name
    django_alias = 'synclogs'


class PhonelogsDBOptions(DBOptions):
    name = constants.phonelogs_db_name
    django_alias = 'phonelogs'


class FormProcessingConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    proxy = jsonobject.ObjectProperty(lambda: FormProcessingProxyDBOptions, required=True)
    partitions = jsonobject.DictProperty(lambda: StrictPartitionDBOptions, required=True)

    @classmethod
    def wrap(cls, data):
        for i, (django_alias, db) in enumerate(data['partitions'].items()):
            db['django_alias'] = db.get('django_alias', django_alias)
            db['name'] = db.get('name', 'commcarehq_{}'.format(db['django_alias']))
        self = super(FormProcessingConfig, cls).wrap(data)
        return self

    def get_db_list(self):
        return [self.proxy] + sorted(self.partitions.values(),
                                     key=lambda db: alphanum_key(db.django_alias))


class FormProcessingProxyDBOptions(DBOptions):
    name = constants.form_processing_proxy_db_name
    django_alias = 'proxy'


class PartitionDBOptions(DBOptions):
    shards = jsonobject.ListProperty(int, exclude_if_none=True)  # [start, end] pair


class CustomDBOptions(PartitionDBOptions):
    django_migrate = jsonobject.BooleanProperty(required=True)


class StandbyDBOptions(PartitionDBOptions):
    hq_acceptable_standby_delay = jsonobject.IntegerProperty(default=None)


class StrictPartitionDBOptions(PartitionDBOptions):
    def validate(self, *args, **kwargs):
        assert re.match(r'p\d+$', self.django_alias)
        assert self.name == 'commcarehq_{}'.format(self.django_alias)
        return super(StrictPartitionDBOptions, self).validate(*args, **kwargs)
