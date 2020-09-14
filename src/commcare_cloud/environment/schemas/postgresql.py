import copy
from collections import defaultdict

import jsonobject
import re

import six

from commcare_cloud.environment.constants import constants
from commcare_cloud.environment.exceptions import PGConfigException
from commcare_cloud.environment.schemas.role_defaults import get_defaults_jsonobject

PostgresqlOverride = get_defaults_jsonobject(
    'postgresql_base',
    allow_dump_from_pgstandby=jsonobject.BooleanProperty,
)

PgbouncerOverride = get_defaults_jsonobject('pgbouncer')


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


DEFAULT_POSTGRESQL_USER = "{{ postgres_users.commcare.username }}"
DEFAULT_POSTGRESQL_PASSWORD = "{{ postgres_users.commcare.password }}"
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
    replications = jsonobject.ListProperty(lambda: LogicalReplicationOptions, required=False)

    postgres_override = jsonobject.ObjectProperty(PostgresqlOverride)
    pgbouncer_override = jsonobject.ObjectProperty(PgbouncerOverride)

    # Mapping of host to list of databases to run pg_repack on
    pg_repack = jsonobject.DictProperty()

    @classmethod
    def wrap(cls, data):
        # for better validation error message
        PostgresqlOverride.wrap(data.get('postgres_override', {}))
        PgbouncerOverride.wrap(data.get('pgbouncer_override', {}))
        [LogicalReplicationOptions(_data) for _data in data.get('replications', [])]
        self = super(PostgresqlConfig, cls).wrap(data)
        for db in self.generate_postgresql_dbs():
            if not db.user:
                db.user = DEFAULT_POSTGRESQL_USER
            if not db.password:
                db.password = DEFAULT_POSTGRESQL_PASSWORD
        return self

    def to_generated_variables(self, environment):
        data = self.to_json()
        del data['postgres_override']
        del data['pgbouncer_override']
        data['postgresql_dbs'] = data.pop('dbs')

        sorted_dbs = sorted(
            (db.to_json() for db in self.generate_postgresql_dbs()),
            key=lambda db: db['name']
        )
        data['postgresql_dbs']['all'] = sorted_dbs
        data.update(self.postgres_override.to_json())
        data.update(self.pgbouncer_override.to_json())

        # generate list of databases per host for use in pgbouncer and postgresql configuration
        postgresql_hosts = environment.groups.get('postgresql', [])
        if self.DEFAULT_POSTGRESQL_HOST not in postgresql_hosts:
            postgresql_hosts.append(self.DEFAULT_POSTGRESQL_HOST)
        postgresql_hosts.extend(environment.groups.get('citusdb_master', []))

        dbs_by_host = defaultdict(list)
        for db in sorted_dbs:
            if db['pgbouncer_host'] in postgresql_hosts:
                dbs_by_host[db['pgbouncer_host']].append(db)

        for host in environment.groups.get('pg_standby', []):
            root_pg_host = self._get_root_pg_host(host, environment)
            dbs_by_host[host] = dbs_by_host[root_pg_host]

        for host in environment.groups.get('citusdb_worker', []):
            citusdb_masters = set(environment.groups.get('citusdb_master', []))
            pg_standbys = set(environment.groups.get('pg_standby', []))
            citusdb_master = list(citusdb_masters - pg_standbys)[0]
            citus_dbs = []
            for db in sorted_dbs:
                if db['host'] == citusdb_master:
                    db_config = copy.deepcopy(db)
                    db_config['host'] = host
                    db_config['pgbouncer_host'] = host
                    citus_dbs.append(db_config)

            dbs_by_host[host] = citus_dbs

        data['postgresql_dbs']['by_host'] = dict(dbs_by_host)
        return data

    def _get_root_pg_host(self, standby_host, env):
        standby_host = env.translate_host(standby_host, env.paths.inventory_source)
        vars = env.get_host_vars(standby_host)
        standby_master = vars.get('hot_standby_master')
        if not standby_master:
            raise PGConfigException('{} has not root PG host'.format(standby_host))
        standby_master = env.translate_host(standby_master, env.paths.inventory_source)
        potential_masters = env.groups['postgresql'] + env.groups.get('citusdb',[])
        if standby_master in potential_masters:
            return standby_master
        return self._get_root_pg_host(standby_master, env)

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

        all_dbs = self.generate_postgresql_dbs()
        for db in all_dbs:
            if db.host is None:
                db.host = self.DEFAULT_POSTGRESQL_HOST
            elif db.host != '127.0.0.1':
                db.host = environment.translate_host(db.host, environment.paths.postgresql_yml)

            if db.pgbouncer_host is None:
                db.pgbouncer_host = db.host
            else:
                db.pgbouncer_host = environment.translate_host(db.pgbouncer_host, environment.paths.postgresql_yml)
            if db.port is None:
                if db.host in host_settings:
                    db.port = host_settings[db.host].port
                else:
                    db.port = DEFAULT_PORT

        pg_repack = {
            environment.translate_host(host, environment.paths.postgresql_yml): databases
            for host, databases in self.pg_repack.items()
        }
        self.pg_repack = pg_repack

        for replication in self.replications:
            replication.source_host = environment.translate_host(replication.source_host, environment.paths.postgresql_yml)
            replication.target_host = environment.translate_host(replication.target_host, environment.paths.postgresql_yml)

        for entry in self.postgres_override.postgresql_hba_entries:
            netmask = entry.get('netmask')
            if netmask and not re.match(r'(\d+\.?){4}', netmask):
                host, mask = netmask.split('/')
                host = environment.translate_host(host, environment.paths.postgresql_yml)
                entry['netmask'] = '{}/{}'.format(host, mask)

        all_dbs_by_alias = {db.django_alias: db for db in all_dbs}
        for db in self.dbs.standby:
            if not db.name and db.master in all_dbs_by_alias:
                db.name = all_dbs_by_alias[db.master].name

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

    def _check_standbys(self):
        if self.dbs.standby:
            defined_django_aliases = {
                db.django_alias: db for db in self.generate_postgresql_dbs()
                if db.django_alias is not None
            }
            for db in self.dbs.standby:
                master_db = defined_django_aliases.get(db.master)
                assert master_db, \
                    'Standby databases reference missing masters: {}'.format(db.master)
                assert master_db.name == db.name, \
                    'Master and standby have different names: {}'.format(db.django_alias)

    def check(self):
        self._check_reporting_databases()
        self._check_shards()
        self._check_standbys()
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

    custom = jsonobject.ListProperty(lambda: CustomDBOptions)
    standby = jsonobject.ListProperty(lambda: StandbyDBOptions)


class PGConfigItem(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty()
    value = jsonobject.DefaultProperty()


class DBOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False

    name = jsonobject.StringProperty(required=True)
    host = jsonobject.StringProperty()
    pgbouncer_host = jsonobject.StringProperty(default=None)
    port = jsonobject.IntegerProperty(default=None)
    user = jsonobject.StringProperty()
    password = jsonobject.StringProperty()
    options = jsonobject.DictProperty(unicode)
    django_alias = jsonobject.StringProperty()
    django_migrate = jsonobject.BooleanProperty(default=True)
    query_stats = jsonobject.BooleanProperty(default=False)
    create = jsonobject.BooleanProperty(default=True)

    # config values to be set at the database level
    pg_config = jsonobject.ListProperty(lambda: PGConfigItem)


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


class FormProcessingConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    proxy = jsonobject.ObjectProperty(lambda: FormProcessingProxyDBOptions, required=True)
    proxy_standby = jsonobject.ObjectProperty(lambda: FormProcessingStandbyProxyDBOptions, required=False)
    partitions = jsonobject.DictProperty(lambda: StrictPartitionDBOptions, required=True)

    @classmethod
    def wrap(cls, data):
        for i, (django_alias, db) in enumerate(data['partitions'].items()):
            db['django_alias'] = db.get('django_alias', django_alias)
            db['name'] = db.get('name', 'commcarehq_{}'.format(db['django_alias']))
        self = super(FormProcessingConfig, cls).wrap(data)
        return self

    def get_db_list(self):
        return (
            [self.proxy]
            + ([self.proxy_standby] if self.proxy_standby.host else [])
            + sorted(self.partitions.values(), key=lambda db: alphanum_key(db.django_alias))
        )


class FormProcessingProxyDBOptions(DBOptions):
    name = constants.form_processing_proxy_db_name
    django_alias = 'proxy'


class FormProcessingStandbyProxyDBOptions(DBOptions):
    name = constants.form_processing_proxy_standby_db_name
    django_alias = 'proxy_standby'


class PartitionDBOptions(DBOptions):
    shards = jsonobject.ListProperty(int, exclude_if_none=True)  # [start, end] pair


class CustomDBOptions(PartitionDBOptions):
    django_migrate = jsonobject.BooleanProperty(required=True)


class StandbyDBOptions(PartitionDBOptions):
    name = jsonobject.StringProperty()
    master = jsonobject.StringProperty(required=True)
    acceptable_replication_delay = jsonobject.IntegerProperty(default=None)
    create = False
    django_migrate = False


class LogicalReplicationOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    target_host = jsonobject.StringProperty(required=True)
    target_db_name = jsonobject.StringProperty(required=True)
    source_host = jsonobject.StringProperty(required=True)
    source_db_name = jsonobject.StringProperty(required=True)
    replication_set = jsonobject.ListProperty(int, required=True)  # [start, end] pair


class StrictPartitionDBOptions(PartitionDBOptions):
    def validate(self, *args, **kwargs):
        assert re.match(r'p\d+$', self.django_alias)
        assert self.name == 'commcarehq_{}'.format(self.django_alias)
        return super(StrictPartitionDBOptions, self).validate(*args, **kwargs)
