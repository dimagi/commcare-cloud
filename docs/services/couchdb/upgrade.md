# Upgrading CouchDB 

* Current default version: 2.3.1
* Example target version: 3.1.1 

Refer to [CouchDB Upgrade documentation](https://docs.couchdb.org/en/stable/install/upgrading.html) for more details.

1. Ensure that the CouchDB config is up to date

    ```
    $ cchq <env> ap deploy_couchdb2.yml
    ```

2. Update the CouchDB version number in `public.yml`

    **environments/<env>/public.yml**
    ```
    couch_version: 3.1.1  
    ```

3. Upgrade the CouchDB on rolling basis one by one on each couchDB nodes

    ```
    $ cchq <env> ap deploy_couchdb2.yml --limit=couch0(N)
    ```

4. Upgrade the  one node at a time and reboot the node before applying the upgrade on another couchDB node.
   Perform the after-reboot once the node has been rebooted.

   ```
    $ cchq <env> after-reboot couch0(N)
    ```


5. After each node update, check the cluster membership and DB presence on that node using below commands before proceeding with another node:

    
    ```
    $ curl http://<couch-username>:<couch-password>@<node-ip>:15984/_all_dbs|jq '.' 
    ```

    ```
    $ curl http://<couch-username>:<couch-password>@<node-ip>:15984/_membership|jq '.'
    ```
