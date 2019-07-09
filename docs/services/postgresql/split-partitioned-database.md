# Splitting a shard in postgresql

## Assumptions

`pg1` is currently the only database containing sharded data.
Half of the data should be moved to a new `pg2` server

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

## Process Overview

1. Setup *pg2* node as a standby node of *pg1*
2. Promote *pg2* to a master node
3. Update the configuration so that requests for database alias *p2* go to *pg2* instead
of *pg1*.
4. Delete invalid data

## Process detail

### 1. Setup *pg2* as a standby node of *pg1*
This step does not require downtime and can be done at any stage prior to the
downtime.

```bash
commcare-cloud <env> ansible-playbook setup_pg_standby.yml -e standby=pg2 -e hot_standby_master=pg1 -e replication_slot=[replication slot name]
```

### 2. Stop all DB requests
This will bring the CommCare HQ site down.

**Stop all CommCare processes**
```bash
commcare-cloud <env> downtime start
```

**Stop pgbouncer**

```bash
commcare-cloud <env> run-shell-command 'monit stop pgbouncer' --become
```

### 3. Check document counts in the databases
This step is useful for verifying the move at the end.
```
commcare-cloud <env> django-manage print_approximate_doc_distribution --csv
```

### 4. Update database name

In pg2 postgres shell:

```sql
ALTER DATABASE commcarehq_p1 RENAME TO commcarehq_p2;
```

### 5. Update configuration

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
       p1:
-        shards: [0, 3]
+        shards: [0, 1]
         host: pg1
+      p2:
+        shards: [2, 3]
+        host: pg2
       ...
```

**Deploy changes**
```
# update localsettings
commcare-cloud <env> update-config

# update PostgreSQL config on new PG node
commcare-cloud <env> ap deploy_db.yml --limit=pg2
```

### 6. Verify config changes
```
commcare-cloud <env> django-manage print_approximate_doc_distribution --csv
```

This should show that the *p2* database is now on the *pg2* host.

### 7. Promote *pg2* to master

**Verify that replication is up to date**
```
commcare-cloud <env> run-shell-command pg1,pg2 'ps -ef | grep -E "sender|receiver"'

    [ pg1 ] ps -ef | grep -E "sender|receiver"
    postgres 5295 4517 0 Jul24 ? 00:00:01 postgres: wal sender process rep 10.116.175.107(49770) streaming 0/205B598

    [ pg2 ] ps -ef | grep -E "sender|receiver"
    postgres 3821 3808 0 Jul24 ? 00:01:27 postgres: wal receiver process streaming 0/205B598
```

Output shows that master and standby are up to date (both processing the same log).

**Promote *pg2***
```bash
commcare-cloud <env> run-shell-command pg2 -b 'pg_ctlcluster <pg version> main promote'
```


### 8. Verify doc counts
Re-run command from step 6 to verify that the document counts are double the number before.
This is because each shard's data is now in two databases.

### 9. Update pl_proxy config
```
commcare-cloud <env> django-manage configure_pl_proxy_cluster
```

### 10. Remove invalid data
The same data now exists in multiple shards. Run the following command to delete that data

```
commcare-cloud <env> django-manage locate_invalid_shard_data --delete
```

Optionally you can run a vacuum to more reclaim space from the table.

```sql
VACUUM FULL table_name;
```

### 11. Verify doc counts
Re-run command from step 6 to verify that the document counts are the same number as in step 5 (half as in step 8).

### 12. Restart services
**start pgbouncer**

```bash
commcare-cloud <env> run-shell-command 'monit start pgbouncer' --become
```

**Restart services**
```bash
commcare-cloud <env> downtime end
```

### 13. Validate the setup
One way to check that things are working as you expect is to examine the
connections to the databases.

```sql
SELECT client_addr, datname as database, count(*) AS connections FROM pg_stat_activity GROUP BY client_addr, datname;
```

*pg1* should only have connections to the *commcarehq_p1* database
```
  client_addr   | database   | connections
----------------+------------+------------
 <client IP>    | commcarehq_p1 |   3
```

*pg2* should only have connections to the *commcarehq_p2* database
```
  client_addr   | database   | connections
----------------+------------+------------
 <client IP>    | commcarehq_p2 |   3
```

---

[︎⬅︎ PostgreSQL](../postgresql.md) | [︎⬅︎ Overview](../..)
