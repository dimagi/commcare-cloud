# PostgreSQL migration from NIC to TCL

1. Stop nodes

    ```
    $ cchq icds-cas service postgresql stop
    ```

2. Remove postgresql data

    ```
    $ cchq icds-cas run-shell-command postgresql:!plproxy0 "rm -rf /opt/data/postgresql/9.6/main/*" -b
    ```

3. Copy data

    ```
    cchq icds-cas copy-files environments/icds-cas/migrations/postgresql-files.yml prepare
    cchq icds-cas copy-files environments/icds-cas/migrations/postgresql-files.yml copy
    cchq icds-cas copy-files environments/icds-cas/migrations/postgresql-files.yml cleanup
    ```

4. Start PG on new nodes

    ```
    $ cchq icds-cas service postgresql start
    ```

5. Perform full VACUUM on each node
    
    ```
    cchq icds-cas run-shell-command postgresql "vacuumdb -a -f -z -w" -b --become-user=postgres
    ```
    
6. Cleanup replication slots

    ```
    cchq icds-cas run-module postgresql pg_replication_slot "name=standby state=absent" -b --become-user postgres
    cchq icds-cas ap deploy_db.yml --tags replication --limit postgresql
    ```

7. Setup standby nodes
    ```
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgmainstandby0

    cchq icds-cas ap setup_pg_standby.yml -e standby=pgucrstandby0
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgucrstandby1
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgucrstandby2
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgucrstandby3

    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard0standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard1standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard2standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard3standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard4standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard5standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard6standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard7standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard8standby
    cchq icds-cas ap setup_pg_standby.yml -e standby=pgshard9standby

    cchq icds-cas ap setup_pg_standby.yml -e standby=pgsynclog0standby
    ```
