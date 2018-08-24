# CouchDB migration from NIC to TCL

1. Stop nodes

    ```
    $ cchq icds-cas service couchdb2 stop
    ```

2. Remove couch data

    ```
    $ cchq icds-cas run-shell-command couchdb2 -b "rm -rf /opt/data/couchdb2/*"
    ```

3. Run migration
    ```
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml describe
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml plan
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml migrate
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml commit
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml clean
    ```
