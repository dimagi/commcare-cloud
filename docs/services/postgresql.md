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
  
{::comment}
Would be nice to get a diagram in here.
{:/comment}

## Configuration

The configuration of PostgreSQL is done via the 
[postgresql.yml](../commcare-cloud/env/postgresql_yml.md) environment
file.

## Advanced tasks

- [Backup PostgreSQL](postgresql/add-barman-server.md)
- [Moving partitioned databases](postgresql/move-partitioned-database.md)

---

[︎⬅︎ Overview](..)
