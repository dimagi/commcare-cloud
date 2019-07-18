# Adding a postgresql hot standby node

The PostgreSQL standby is a hot standby (accept reads operations only) of each production database. Each Database node should have standby node configured and deployed. This will require configuring in the environment inventory files to set variables as follows:

 #### On primary node 
 Add
  * `hot_standy_server` (points to standby server)
  * `postgresql_replication_slots` (list of replication slots)
    * replication slots should be formatted a list as follows:
      * CSV invenory: "[""slot1"",""slot2""]"
      * INI inventory: ["slot1","slot2"]


#### On the standby node 
Add
* `hot_standby_master` (point to primary)
* `replication_slot` (which replication slot to use)

To deploy the standby nodes we'd first need to create the replication slots in the primary.

```
$ cchq icds run-shell-command <master-node> --become-user=postgres "psql -d icds_ucr -c  "'"'"SELECT * FROM pg_create_physical_replication_slot('<slot name>')"'"'""
```

After that we can use the `setup_pg_standby.yml` playbook
```
$ cchq <env> ap setup_pg_standby.yml -e standby=[standby node]
```


# Promoting a hot standby to Master
```
$ cchq <env> ansible-paybook promote_pg_standby.yml -e standy=[standby nde]
```
