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


# Promoting a hot standby to master

1. In your inventory you have two postgresql servers defined:

    * `pg_database` with `postgresql_replication_slots = ["standby0"]`
    * `pg_standby` where `hot_standby_master = pg_database` and `replication_slot = "standby0"`

2. Begin downtime for your site:

    ```bash
    $ commcare-cloud <env> downtime start
    ```

3. Verify that the replication is up to date

   ```bash
   $ commcare-cloud <env> run-shell-command pg_database,pg_standby 'ps -ef | grep -E "sender|receiver"'
       [ pg_database ] ps -ef | grep -E "sender|receiver"
       postgres 5295 4517 0 Jul24 ? 00:00:01 postgres: wal sender process rep 10.116.175.107(49770) streaming 0/205B598
       [ pg_standby ] ps -ef | grep -E "sender|receiver"
       postgres 3821 3808 0 Jul24 ? 00:01:27 postgres: wal receiver process streaming 0/205B598
   ```

   Output shows that master and standby are up to date (both processing the same log).

4. Promote the standby

    ```bash
    $ commcare-cloud <env> ansible-paybook promote_pg_standby.yml -e standby=pg_standby
    ```

5. In your inventory remove `hot_standby_master` and `replication_slot` variables from your standby node,
    and move the node from the `pg_standby` group to the `postgresql` group.

6. Update the host for the applicable database(s) in `postgresql.yml` and update your processes to point to the newly
    promoted server:

    ```bash
    $ commcare-cloud <env> update-config
    ```

7. If the standby you've promoted is one of the `form_processing` databases update the PL proxy cluster configuration:

    ```bash
    $ commcare-cloud <env> django-manage --tmux configure_pl_proxy_cluster
    ```

8. [Optional] If you have configured your standby and master nodes to use different parameters, or
    you would like to create replication slots on the newly promoted standby update those configurations:

    ```bash
    $ commcare-cloud <env> ap deploy_db.yml --limit pg_database,pg_standby
    ```

9. End downtime for your site:

    ```bash
    $ commcare-cloud <env> downtime end
    ```

10. If you would like to have another standby for this newly promoted master, follow above instructions for adding a standby database.
