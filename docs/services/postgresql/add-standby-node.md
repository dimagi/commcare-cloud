# Adding a postgresql hot standby node

The PostgreSQL standby is a hot standby (accept reads operations only) of each production database. Each Database node should have standby node configured and deployed. This will require configuring in the environment inventory files to set variables as follows:

#### On primary node 
* `hot_standy_server` (points to standby server)
* `postgresql_replication_slots` (list of replication slots)
  * replication slots should be formatted a list as follows:
    * CSV invenory: "[""slot1"",""slot2""]"
    * INI inventory: ["slot1","slot2"]


#### On the standby node 
* `hot_standby_master` (point to primary)
* `replication_slot` (which replication slot to use)
* Add node to `pg_standby` group

To deploy the standby nodes we'd first need to create the replication slots in the primary.
We normally use ansible playbook to perform this
```
$ commcare-cloud ap deploy_postgresql.yml --limit <primary host>
```
Note:- In case if a restart is not desired then this command can be used.
```
$ commcare-cloud <env> run-shell-command <primary-node> -b --become-user=postgres "psql -d <database name> -c  "'"'"SELECT * FROM pg_create_physical_replication_slot('<slot name>')"'"'""
```

After that we can use the `setup_pg_standby.yml` playbook
```
$ cchq <env> ap setup_pg_standby.yml -e standby=[standby node]
```


# Promoting a hot standby to Master
1. Begin downtime for your site: `$ commcare-cloud <env> downtime start`

2. Verify that the replication is up to date

```
$ commcare-cloud <env> run-shell-command pg1,pg2 'ps -ef | grep -E "sender|receiver"'

    [ pg1 ] ps -ef | grep -E "sender|receiver"
    postgres 5295 4517 0 Jul24 ? 00:00:01 postgres: wal sender process rep 10.116.175.107(49770) streaming 0/205B598

    [ pg2 ] ps -ef | grep -E "sender|receiver"
    postgres 3821 3808 0 Jul24 ? 00:01:27 postgres: wal receiver process streaming 0/205B598
```

Output shows that master and standby are up to date (both processing the same log).

3. Promote the standby

```
$ commcare-cloud <env> ansible-paybook promote_pg_standby.yml -e standy=[standby node]
```

4. In your inventory remove `hot_standby_master` and `replication_slot` variables from your standby node, and remove the node from the `pg_standby` group.

5. Update your processes to point to the newly promoted server:

```
$ commcare-cloud <env> update-config
```

6. If the standby you've promoted is one of the `form_processing` databases, update the PL proxy cluster

```
$ commcare-cloud <env> django-manage --tmux configure_pl_proxy_cluster
```

7. If you have configured your standby and master nodes to use different parameters, or
you would like to create replication slots on the newly promoted standby update those configurations:

```
$ commcare-cloud <env> ap deploy_db.yml --limit pg1,pg2
```

8. End downtime for your site: `$ commcare-cloud <env> downtime end`

9. If you would like to have another standby for this newly promoted master, follow above instructions for adding a standby database.


# Troubleshooting

## Replication Delay
https://www.enterprisedb.com/blog/monitoring-approach-streaming-replication-hot-standby-postgresql-93

* Check if wal receiver and sender process are running respectively on standby and master using `ps aux | grep receiver` and `ps aux | grep sender`
* Alternatively use SQL `select * from pg_stat_replication` on either master or standby
* If WAL processes are not running, check logs, address any issues and may need to reload/restart postgres
* Check logs for anything suspicious
* Checking replication delay
  * [Use datadog](https://app.datadoghq.com/dash/263336/postgres---overview?live=true&page=0&is_auto=false&from_ts=1511770050831&to_ts=1511773650831&tile_size=m&tpl_var_env=*&fullscreen=253462140&tpl_var_host=*)
  * Run queries on nodes:

```sql
--- on master
select
  slot_name,
  client_addr,
  state,
  pg_size_pretty(pg_xlog_location_diff(pg_current_xlog_location(), sent_location)) sending_lag,
  pg_size_pretty(pg_xlog_location_diff(sent_location, flush_location)) receiving_lag,
  pg_size_pretty(pg_xlog_location_diff(flush_location, replay_location)) replaying_lag,
  pg_size_pretty(pg_xlog_location_diff(pg_current_xlog_location(), replay_location)) total_lag
from pg_replication_slots s
left join pg_stat_replication r on s.active_pid = r.pid
where s.restart_lsn is not null;

-- On standby

SELECT now() - pg_last_xact_replay_timestamp() AS replication_delay;
```

In some cases it may be necessary to restart the standby node.
