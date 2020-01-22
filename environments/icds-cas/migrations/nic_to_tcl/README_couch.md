# CouchDB migration from NIC to TCL

1. Stop nodes

    ```
    $ cchq icds-cas service couchdb2 stop
    ```

2. Remove couch data from new nodes

    ```
    $ cchq icds-cas run-shell-command couchdb2 -b "rm -rf /opt/data/couchdb2/*"
    ```

3. Run migration

  * Automated migration

    This uses the [migrate-couchdb](https://dimagi.github.io/commcare-cloud/commcare-cloud/commands/#migrate-couchdb) command which will handle copying the data as well as updating
    the database configuration.

    ```
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb.yml describe
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb.yml plan
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb.yml migrate
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb.yml commit
    cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb.yml clean
    ```

  * Manual migration (not recommended)
    
    This replicates the steps done by the automated migration command in a more manual fashion.
    
    1. Copy data
        ```
        cchq icds-cas copy-files environments/icds-cas/migrations/nic_to_tcl/couchdb-files.yml prepare
        cchq icds-cas copy-files environments/icds-cas/migrations/nic_to_tcl/couchdb-files.yml copy
        cchq icds-cas copy-files environments/icds-cas/migrations/nic_to_tcl/couchdb-files.yml cleanup
        ```
    
    2. Update database
       
        This is necessary in order to update the database files with the new cluster IP addresses.
        
        ```
        python environments/icds-cas/migrations/nic_to_tcl/couchdb-files-post.py <username>
        ```
    
    3. Run migration to copy data to 5th node
        ```
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb-files-plan.yml describe
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb-files-plan.yml plan
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb-files-plan.yml migrate
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb-files-plan.yml commit
        cchq icds-cas migrate-couchdb environments/icds-cas/migrations/nic_to_tcl/couchdb-files-plan.yml clean
        ```
