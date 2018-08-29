# CouchDB migration from NIC to TCL

1. Stop nodes

    ```
    $ cchq icds-cas service couchdb2 stop
    ```

2. Remove couch data

    ```
    $ cchq icds-cas run-shell-command couchdb2 -b "rm -rf /opt/data/couchdb2/*"
    ```

3a. Run migration (or do 3b)
    ```
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml describe
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml plan
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml migrate
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml commit
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb.yml clean
    ```

3b. File system level copy

    1. Copy data
        ```
        cchq icds-cas copy-files environments/icds-cas/migrations/couchdb-files.yml prepare
        cchq icds-cas copy-files environments/icds-cas/migrations/couchdb-files.yml copy
        cchq icds-cas copy-files environments/icds-cas/migrations/couchdb-files.yml cleanup
        ```
    
    2. Update database
        ```
        python environments/icds-cas/migrations/couchdb-files-post.py <username>
        ```
    
    3. Run migration to copy data to 5th node
        ```
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb-files-plan.yml describe
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb-files-plan.yml plan
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb-files-plan.yml migrate
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb-files-plan.yml commit
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/couchdb-files-plan.yml clean
        ```
