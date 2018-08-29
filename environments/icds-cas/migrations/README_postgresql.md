# PostgreSQL migration from NIC to TCL

1. Stop nodes

    ```
    $ cchq icds-cas service postgresql stop
    ```

2. Remove postgresql data

    ```
    $ cchq icds-cas run-shell-command postgresql "rm -rf /opt/data/postgresql/9.6/main/*" -b
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
