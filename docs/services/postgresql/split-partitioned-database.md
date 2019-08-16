# Splitting a shard in postgresql

This document describes the process required to split a partitioned database
from one PostgreSQL instance into itself and another. This migration will
require downtime.

## Assumptions

For the purposes of this document we'll assume that we have three database machines, *pg1*
, *pg2* and *pg3*. *pg1* has one database and *pg2* and *pg3* has none:

*pg1* databases:

* *commcarehq_p1* (with django alias *p1*)

*pg2* and *pg3* is a newly deployed server in the *[postgresql]* group and we want to
create a new  *commcarehq_p2* on *pg2*  and *commcarehq_p3* on *pg3* with half the data from *commcarehq_p1* on each.

*pg1* is currently the only database containing sharded data.
Half of the data should be moved to a new *pg2* and *pg3* servers

Current database configuration:

```python
PARTITION_DATABASE_CONFIG = {
    'shards': {
        'p1': [0, 3],
    },
    'groups': {
        'main': ['default'],
        'proxy': ['proxy'],
        'form_processing': ['p1'],
    },
}

DATABASES = {
    'proxy': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'commcarehq_proxy',
        'USER': 'commcarehq',
        'PASSWORD': 'commcarehq',
        'HOST': 'pg1',
        'PORT': '5432',
        'TEST': {
            'SERIALIZE': False,
        },
    },
    'p1': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'commcarehq_p1',
        'USER': 'commcarehq',
        'PASSWORD': 'commcarehq',
        'HOST': 'pg1',
        'PORT': '5432',
        'TEST': {
            'SERIALIZE': False,
        },
    },
}
```

At the end of this process shards 0 & 1 should be on *pg2* and shards 2 & 3 will be on *pg3*.

## Process Overview

1. Ensure that *pg1* is set to use logical replication
2. Setup *pg2* and *pg3* as a new database
3. Setup logical replication from pg1 to pg2 and pg3
4. Promote *pg2* and *pg3* to a master node
5. Update the applications configuration to go to *pg2* and *pg3*

## Process detail

### 1. Setup logical replication on *pg1*

In your configuration set the following and deploy the configuration to *pg1*:

```
[pg1]
...
postgresql_wal_level = logical
postgresql_max_worker_processes = 8
postgresql_shared_preload_libraries = ["pglogical"]
```

Also ensure that your replication user has superuser privileges on all databases, in vault.yml:

```yaml
POSTGRES_USERS:
  replication:
    username: 'foo'
    password: 'bar'
    role_attr_flags: 'LOGIN,REPLICATION,SUPERUSER'
```

In postgresql.yml:

```yaml
postgresql_hba_entries:
  - contype: host
    users: foo
    netmask: 'pg2 ip address'
  - contype: host
    databases: replication
    users: foo
    netmask: 'pg2 ip address'
```

### 2. Setup *pg2* and *pg3*

Setup *pg2* and *pg3* as you would another postgresql database in commcare-cloud.

In addition to normal setup, add the following your postgresql.yml file:

```yaml
dbs:
  logical:
    - name: commcarehq_p2
      host: pg2
      master_host: pg1
      master_db_name: commcarehq_p1
      replication_set: [0, 1]
    - name: commcarehq_p3
      host: pg3
      master_host: pg1
      master_db_name: commcarehq_p1
      replication_set: [2, 3]
```

Deploy this change to your databases using:


```bash
commcare-cloud <env> ap setup_pg_logical_replication.yml
```

This will begin the replication process in the background. To check the progress:

```bash
commcare-cloud <env> run-shell-command pg2 -b --become-user=postgres "psql -d commcarehq_p2 -c  "'"'"SELECT * FROM pglogical.show_subscription_status()"'"'""
```
# TODO Add example output

### 3. Stop all DB requests
Once the databases are fully replicated and you are ready to switch to the new databases, bring the site down.

**Stop all CommCare processes**
```bash
commcare-cloud <env> downtime start
```

**Stop pgbouncer**

```bash
commcare-cloud <env> run-shell-command pg1,pg2,pg3 'monit stop pgbouncer' --become
```

### 4. Update configuration

**Update ansible config**

Update the *dbs* variable in the environment's *postgresql.yml* file
to show that the *p2* database is now on *pg2*:


```diff
...
 dbs:
 ...
   form_processing:
     ...
     partitions:
-      p1:
-        shards: [0, 3]
-        host: pg1
+      p2:
+        shards: [0, 1]
+        host: pg2
+      p3:
+        shards: [2, 3]
+        host: pg3
       ...
```

**Deploy changes**
```
# update localsettings
commcare-cloud <env> update-config

# update PostgreSQL config on new PG node
commcare-cloud <env> ap deploy_db.yml --limit=pg2,pg3

# update the pl_proxy cluster
commcare-cloud <env> django-manage --tmux configure_pl_proxy_cluster
```

### 5. Restart services
**start pgbouncer**

```bash
commcare-cloud <env> run-shell-command pg1,pg2,pg3 'monit start pgbouncer' --become
```

**Restart services**
```bash
commcare-cloud <env> downtime end
```

---

[︎⬅︎ PostgreSQL](../postgresql.md) | [︎⬅︎ Overview](../..)
