# Moving a PostgreSQL sharded database

For large scale deployments of CommCare HQ the database tables that contain
case and form (and related) data can be partitioned between multiple PostgreSQL databases.

To ease the burden of scaling it is common to create as many databases as necessary
up front since splitting databases is much more difficult than moving databases. In
this case a deployment of CommCare HQ may start with a single database server
that contains all the databases. As the project scales up more database servers
can be added and the databases can be moved to spread the load.

This document describes the process required to move a database from one PostgreSQL
instance to another.

For the purposes of this document we'll assume that we have two database machines, *pg1*
and *pg2*. *pg1* has two partitioned databases and *pg2* has none:

*pg1* databases:

* *commcarehq_p1* (with django alias *p1*)
* *commcarehq_p2* (with django alias *p2*)

*pg2* is a newly deployed server and we want to move *commcarehq_p2* onto *pg2*.

## Assumptions

* *pg2* has been added to the Ansible inventory and included in the *[postgresql]* group
* *pg2* has had a full stack Ansible deploy
* *pg1* has a [replication slot][] available

[replication slot]: https://www.postgresql.org/docs/current/static/warm-standby.html#STREAMING-REPLICATION-SLOTS

## Process Overview

1. Setup *pg2* node as a standby node of *pg1*
3. Promote *pg2* to a master node
4. Update the configuration so that requests for *p2* go to *pg2* instead
of *pg1*.

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
commcare-cloud <env> fab supervisorctl:"stop all"
```

You may have to wait for any long running celery tasks to complete. You can list any
celery workers that are still running using the following commands:

```
commcare-cloud <env> django-manage show_celery_workers
commcare-cloud <env> run-shell-command celery "ps -ef | grep celery"
```

**Stop pgbouncer**
To be completely certain that no data will be updating during the move you can also
prevent connections from pgbouncer:

```bash
pg1 $ psql -p 6432 -U someuser pgbouncer

> PAUSE commcarehq_p1
```

### 3. Check document counts in the databases
This step is useful for verifying the move at the end.
```
commcare-cloud <env> django-manage print_approximate_doc_distribution --csv
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
       p1:
         shards: [0, 1]
         host: pg1
       p2:
         shards: [2, 3]
-        host: pg1
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

### 5. Verify config changes
```
commcare-cloud <env> django-manage print_approximate_doc_distribution --csv
```

This should show that the *p2* database is now on the *pg2* host.

### 6. Promote *pg2* to master

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


### 7. Verify doc counts
Re-run command from step 5 to verify that the document counts are the same.

### 8. Update pl_proxy config
```
commcare-cloud <env> django-manage configure_pl_proxy_cluster
```

### 9. Restart services
**Unpause pgbouncer**
```bash
pg1 $ psql -p 6543 -U someuser pgbouncer

> RESUME commcarehq_p1
```

**Restart services**
```bash
commcare-cloud <env> fab supervisorctl:"start all"
```

### 10. Validate the setup
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

### 11. Cleanup
**Delete duplicate databases**

Once you're confident that everything is working correctly you can go back
and delete the duplicate databases on *pg1* and *pg2*.

*pg1*

```sql
DROP DATABASE commcarehq_p2;
```

*pg2*

```sql
DROP DATABASE commcarehq_p1;
```


**Drop replication slot**

In order to prevent the WAL logs on *pg1* from piling up we need to delete
the replication slot that was used by *pg2*:

```
commcare-cloud <env> run-shell-command p1 -b --become-user postgres 'psql -c "select pg_drop_replication_slot('\'<slot name>\'');"'

# optionally re-create the slot
commcare-cloud <env> run-shell-command p1 -b --become-user postgres 'psql -c "select pg_create_physical_replication_slot('\'<slot name>\'');"'
```

**Update PostgreSQL config**
```
commcare-cloud <env> ap deploy_db.yml --limit=postgresql
```

## Other useful commands

**Check which nodes are in recovery**
```
commcare-cloud <env> run-shell-command postgresql -b --become-user postgres "psql -c 'select pg_is_in_recovery();'"
```

**Check replication slot status**
```
commcare-cloud <env> run-shell-command postgresql -b --become-user postgres "psql -c 'select * from pg_replication_slots;'"
```

---

[︎⬅︎ PostgreSQL](../postgresql.md) | [︎⬅︎ Overview](../..)
