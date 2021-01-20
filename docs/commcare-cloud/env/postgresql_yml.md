# `<env>/postgresql.yml`

For an example `postgresql.yml` file see
[environments/production/postgresql.yml](https://github.com/dimagi/commcare-cloud/blob/master/environments/production/postgresql.yml).

The following properties are permitted in `postgresql.yml`.

You may notice that some of the properties have a **Status**, which can be either
"Custom" or "Deprecated".
A status of **Custom** means that the property is a back-door for a heavily
customized environment, and should not used in a typical environment.
A status of **Deprecated** means that the property exists to support legacy environments
that have not yet adopted a new standard, and support may be removed for it in the future;
a typical new enviornment should not set these properties either.

## `dbs`

Database-level config such as what machine each db is on.
All properties rely on a conceptual "db config" type described in more detail
below.
 
### `main`
- Type: [db config](#db-config-type)
- Default values:
  ```yaml
  django_alias: default
  name: commcarehq
  django_migrate: True
  ```

Configuration for the main db, the db that the majority of tables live in.

### `formplayer`
- Type: [db config](#db-config-type)
- Default values:
  ```yaml
  django_alias: null
  name: formplayer
  ```

Configuration for the db that formplayer uses
(which does not appear in Django settings).

### `ucr`
- Type: [db config](#db-config-type)
- Default values:
  ```yaml
  django_alias: ucr
  name: commcarehq_ucr
  django_migrate: False
  ```

Configuration for the db that UCRs are copied into.

### `synclogs`
- Type: [db config](#db-config-type)
- Default values:
  ```yaml
  django_alias: synclogs
  name: commcarehq_synclogs
  django_migrate: True
  ```

Configuration for the db that synclog tables live in.

### `form_processing`
- Type: see below
Configuration for the db that form, case, and related tables live in.

It is broken down into the proxy config and the config for partitions

#### `proxy`
- Type: [db config](#db-config-type) with defaults:
- Default values:
  ```yaml
  django_alias: proxy
  name: commcarehq_proxy
  ```

Configuration for the proxy db in the partitioned setup.

#### `proxy_standby`
- Type: [db config](#db-config-type) with defaults:
- Default values:
  ```yaml
  django_alias: proxy_standby
  name: commcarehq_proxy_standby
  ```

Configuration for the proxy db in the partitioned setup which can be used to
query the standby partitions.

#### `partitions`
- Type: dict of partition name to (augmented) [db config](#db-config-type)

Configurations for each of the partitions of the database.
These special configs are augmented with the following property.
Partition names must be `p1`, `p2`, ..., `p<N>`.

##### `shards`
- Type: pair of integers (list with two elements)

Inclusive start and end indices for the shard range.
The `shards` property for all `partitions` combined must cover
the entire range of available shards, and the ranges must be in ascending order
matching the order of the names of the partitions (`p1`, `p2`, ..., `p<N>`).

### "db config" type
The core data type used repeatedly in this configuration is a db config,
which has the following properties:

#### `django_alias`
- Type: string

Alias for the database. Used as the key for the entry in Django
[`DATABASES`](https://docs.djangoproject.com/en/2.0/ref/settings/#databases) setting.
Most aliases are preset, but for custom databases this can be specified.
If missing, the database will not appear in Django settings.


#### `name`
- Type: string

Name of the postgresql database.
(See [`NAME`](https://docs.djangoproject.com/en/2.0/ref/settings/#name).)

#### `host`
- Type: [host string](glossary#host-string)

The host machine on which this database should live.
(See [`HOST`](https://docs.djangoproject.com/en/2.0/ref/settings/#host).)

#### `pgbouncer_host`
- Type: [host string](glossary#host-string)

The host to use to run pgbouncer for this db. Defaults to "host".
Cannot be used if the more granular options `pgbouncer_hosts` and `pgbouncer_endpoints` are set.

#### `pgbouncer_hosts`
- Type: List of [host string](glossary#host-string)

The list of hosts to use to run pgbouncer for this db. Defaults to `[pgbouncer_host]`,
and cannot be set explicitly if `pgbouncer_host` is set. If set explicitly, `pgbouncer_endpoint`
must also be set.

#### `pgbouncer_endpoint` 
- Type: [host string](glossary#host-string)

The endpoint that other processes should use to communicate with pgbouncer for this db.
Defaults to `pgbouncer_host`, and connot be explicitly set if `pgbouncer_host` is set. If set explicitly,
`pgbouncer_hosts` must also be set.

The difference between `pgbouncer_endpoints` and `pgbouncer_hosts` is that `pgbouncer_hosts` says
where pgbouncer should be installed and running for this db, whereas `pgbouncer_endpoints` says
where other machines that want to talk to pgbouncer for this db should point to.
Often these are the same machines in which case you can use `pgbouncer_host` as a shortcut to set both.

Some examples where you would want to set the `pgbouncer_endpoints` and `pgbouncer_hosts` independently:
- You have multiple `pgbouncer_hosts` in a network load balancer whose address `pgbouncer_enpoint` is set to.
- You want `pgbouncer1` to be ready to switch over to in case `pgbouncer0` fails. In that case,
  you set `pgbouncer_hosts` to `[pgbouncer0, pgbouncer1]` and `pgbouncer_endpoint` to `pgbouncer0`.

#### `port`

- Type: int

The port to use when connecting to the database.
(See [`PORT`](https://docs.djangoproject.com/en/2.0/ref/settings/#port).)

#### `user`

- Type: string

The username to use when connecting to the database.
(See [`USER`](https://docs.djangoproject.com/en/2.0/ref/settings/#user).)

#### `password`

- Type: string

The password to use when connecting to the database.
(See [`PASSWORD`](https://docs.djangoproject.com/en/2.0/ref/settings/#password).)

#### `options`
- Type: dict

(See [`OPTIONS`](https://docs.djangoproject.com/en/2.0/ref/settings/#std:setting-OPTIONS).)

#### `django_migrate`
- Type: bool

Whether migrations should be run on this database.
For all except in `custom`, this property is automatically determined.

#### `query_stats`
- Type: bool
- Default: `False`

Whether query statistics should be collected on this PostgreSQL db
using the pg_stat_statements extension.

#### `create`
- Type: bool
- Default: `True`

Whether commcare-cloud should create this db (via Ansible).


## `override`
- Type: dict (variables names to values)

Ansible `postgresql` role variables to override.
See [ansible/roles/postgresql/defaults/main.yml](
https://github.com/dimagi/commcare-cloud/blob/master/ansible/roles/postgresql/defaults/main.yml)
for the complete list of variables.

As with any ansible variable, to override these on a per-host basis,
you may set these as inventory host or group variables in `inventory.ini`.
Note, however, that variables you set there will not receive any validation,
whereas variables set here will be validated against the type
in the defaults file linked above.

## `SEPARATE_SYNCLOGS_DB`

- Type: boolean
- Default: `True`
- Status: Deprecated

Whether to save synclogs to a separate postgresql db.
A value of `False` may lose support in the near future and is not recommended.


## `SEPARATE_FORM_PROCESSING_DBS`

- Type: boolean
- Default: `True`
- Status: Deprecated

Whether to save form, cases, and related data
in a separate set of partitioned postgresql dbs.
A value of `False` may lose support in the near future and is not recommended.

## `DEFAULT_POSTGRESQL_HOST`
- Type: [host string](glossary#host-string)
- Default: The first machine in the `postgresql` inventory group.

This value will be used as the host for any database
without a different host explicitly set in [`dbs`](#dbs).

## `REPORTING_DATABASES`

- Type: dict
- Default: `{"ucr": "ucr"}`
- Status: Custom

Specify a mapping of UCR "engines".

The keys define engine aliases, and can be anything. The values are either

- the `django_alias` of a postgreql database

or

- a spec for which (single) database to write to
  and a weighted list of databases to read from.

The latter option is formatted as follows:


```
WRITE: <django_alias>
READ:
  - [<django_alias>, <weight>]
  - [<django_alias>, <weight>]
  ...
```

where `<weight>` is a low-ish integer.
The probability of hitting a given database with weight W<sub>n</sub> is its normalized weight,
i.e. W<sub>n</sub> / (W<sub>1</sub> + ... + W<sub>N</sub>).

## `LOAD_BALANCED_APPS`

- Type: dict
- Default: `{}`
- Status: Custom

Specify a list of django apps that can be read from multiple dbs.

The keys are the django app label. The values are a weighted list of databases to read from.

This is formatted as:

```
<app_name>:
  - [<django_alias>, <weight>]
  - [<django_alias>, <weight>]
  ...
```

where `<weight>` is a low-ish integer.
The probability of hitting a given database with weight W<sub>n</sub> is its normalized weight,
i.e. W<sub>n</sub> / (W<sub>1</sub> + ... + W<sub>N</sub>).
