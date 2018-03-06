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

* *partition1*
* *partition2*

*pg2* is a newly deployed server and we want to move *partition2* onto *pg2*.

## Assumptions

* *pg2* has been added to the Ansible inventory and included in the *[postgresql]* group
* *pg2* has had a full stack Ansible deploy
* *pg1* has a replication slot available

## Process Overview

1. Setup *pg2* node as a standby node of *pg1*
3. Promote *pg2* to a master node
4. Update the configuration so that requests for *partition2* go to *pg2* instead
of *pg1*.

## Process detail

### 1. Setup *pg2* as a standby node of *pg1*
This step does not require downtime and can be done at any stage prior to the
downtime.

```
commcare-cloud <env> ansible-playbook setup_pg_standby.yml -e standby=pg2 -e hot_standby_master=pg1 -e replication_slot=[replication slot name]
```

### 2. Stop all DB requests
This will bring the CommCare HQ site down.

**Stop all CommCare processes**
```
commcare-cloud <env> fab supervisorctl:"stop all"
```

You may have to wait for any long running celery tasks to complete. You can list any
celery workers that are still running using the following command:

```
commcare-cloud <env> django-manage show_celery_workers
```

**Stop pgbouncer**
To be completely certain that no data will be updating during the move you can also
prevent connections from pgbouncer:

```
$ psql -p 6543 -U someuser pgbouncer

> PAUSE pg1
```

### 3. Check document counts in the databases
This step is useful for verifying the move at the end.
```
commcare-cloud <env> django-manage print_approximate_doc_distribution --csv
```

### 4. Update configuration

**Update ansible config**

Update the *postgresql_dbs* configuration in the environment's *public.yml* file
to show that the *partition2* database is now on *pg2*:


```diff
    postgresql_dbs:
        - django_alias: partition1
          name: partition1
          shards: [0, 1]
          host: "pg1"
        - django_alias: partition2
          name: partition2
          shards: [2, 3]
-         host: pg1
+         host: pg2
```

**Deploy changes**
```
commcare-cloud <env> update-config
```

### 5. Verify config changes
```
commcare-cloud <env> django-manage print_approximate_doc_distribution --csv
```

This should show that the *partition2* database is now on the *pg2* host.

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
```
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
```
$ psql -p 6543 -U someuser pgbouncer

> RESUME pg1
```

**Restart services**
```
commcare-cloud <env> fab supervisorctl:"start all"
```

### 10. Cleanup
Now you can go back and delete the duplicate databases on *pg1* and *pg2*.
