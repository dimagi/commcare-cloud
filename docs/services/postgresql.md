# PostgreSQL
{:.no_toc}

* TOC
{:toc}

## Usage in CommCare

PostgreSQL is one of the primary databases that CommCare uses. 

There are a few different categories of data that are stored in PostgreSQL:

- System level metadata:
  - billing
  - notifications
  - etc
- Project level metadata:
  - users
  - locations
  - etc
- Project generated data:
  - forms
  - cases
  - ledgers
  - message logs
  - formplayer sessions
  - syclogs
- Project reporting data
  - custom report tables
  - standard report tables

CommCare is configured to work with a number of databases:

- `commcarehq`
  - the main 'metadata' database that stores users, locations etc.
- `formplayer`
  - used only by formplayer to store user sessions etc.
- `commcarehq_ucr`
  - custom report database
- `commcarehq_synclogs`
  - data necessary for maintaining the state of the mobile devices 
- `commcarehq_proxy`
  - routing database for sharded databases
  - this is only required for installations that require data sharding due to the scale
- `commcarehq_p[N]`
  - database partition storing cases, forms, ledgers and messaging data
  - there can be any number of these depending on the scale of the installation
  
For small scale installations many of these databases can be combined into a single database.
  
See [CommCare HQ docs](https://commcare-hq.readthedocs.io/databases.html) for more detailed information
on different configurations that CommCare supports.

## Configuration

The configuration of PostgreSQL is done via the 
[postgresql.yml](../commcare-cloud/env/postgresql_yml.md) environment
file.

### Basic setup

- all databases hosted in a single PostgreSQL service
- relies on defaults for most of the databases

```yaml
DEFAULT_POSTGRESQL_HOST: db1
dbs:
  form_processing:
    partitions:
      p1:
        shards: [0, 127]
      p2:
        shards: [128, 255]
      p3:
        shards: [256, 383]
      p4:
        shards: [384, 511]
      p5:
        shards: [512, 639]
      p6:
        shards: [640, 767]
      p7:
        shards: [768, 895]
      p8:
        shards: [896, 1023]
```

### Separate database servers

- `commcarehq`, `formplayer`, `commcarehq_ucr`, `commcarehq_synclogs` hosted on `db1`
- form processing proxy DB (`commcarehq_proxy`) hosted on `plproxy0`
- form processing shard databases split between `pgshard0` and `pgshard1`

```yaml
dbs:
  main:
    host: db1
  formplayer:
    host: db1
  ucr:
    host: db1
  synclogs:
    host: db1
  form_processing:
    proxy:
      host: plproxy0
    partitions:
      p1:
        host: pgshard0
        shards: [0, 127]
      p2:
        host: pgshard0
        shards: [128, 255]
      p3:
        host: pgshard0
        shards: [256, 383]
      p4:
        host: pgshard0
        shards: [384, 511]
      p5:
        host: pgshard1
        shards: [512, 639]
      p6:
        host: pgshard1
        shards: [640, 767]
      p7:
        host: pgshard1
        shards: [768, 895]
      p8:
        host: pgshard1
        shards: [896, 1023]
```

## Advanced tasks

- [Upgrading](postgresql/upgrade.md)
- [Upgrading CitusDB](postgresql/upgrade_citusdb.md)
- [Moving partitioned databases](postgresql/move-partitioned-database.md)
- [Adding hot standby node](postgresql/add-standby-node.md)
- [Migrating plproxy node](postgresql/migrating_plproxy.md)

---

[︎⬅︎ Overview](..)
