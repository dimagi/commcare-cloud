# Add a new CouchDB node to an existing cluster

## Setup the new node and add it to the cluster
1. Update inventory

```diff
+ [couchN]
+ <node ip>

  [couchdb2]
  ...
+ couchN
```

2. Deploy new node

```
commcare-cloud <env> deploy_stack.yml --limit=couchN
```

3. Add node to cluster

```
$ commcare-cloud <env> aps --tags=add_couch_nodes --limit=couchdb2
```

## Migrate database shards to the new node

1. Create a plan

    e.g. 4 nodes with 3 copies of each shard (couchD is the new node)
    ```
    # myplan.yml

    target_allocation:
      - couchA,couchB,couchC,couchD:3
    ```

2. Create new shard plan

    ```
    $ commcare-cloud <env> migrate-couchdb myplan.yml plan
    ```

3. Compare the plan to the current setup

    ```
    $ commcare-cloud <env> migrate-couchdb myplan.yml describe
    ```

    Check that the new cluster layout is what you want. If not adjust
    your plan file and try again.

4. Create migrate (copy data to new node)

    This will shut down all the nodes in the cluster so make sure
    you have initiated downtime prior to this step.

    ```
    $ commcare-cloud <env> migrate-couchdb myplan.yml migrate
    ```

    Alternatively, if you can be confident that the plan keeps
    more than half of the copies of each given shard in place
    (i.e. moves less than half of the copies of each given shard)
    then you can use the `--no-stop` flag,
    and the migration will be done with no downtime.

5. Commit the changes

    This will update the DB docs to tell Couch about the new shard
    allocation.

    ```
    $ commcare-cloud <env> migrate-couchdb myplan.yml commit
    ```

6. Verify

    ```
    $ commcare-cloud <env> migrate-couchdb myplan.yml describe
    ```

7. Redeploy Proxy 

    ```
    $ commcare-cloud <env> ansible-playbook deploy_couchdb2.yml --tags=proxy
    ```

## Cleanup

After confirming that all is well we can remove old shards:

```
$ commcare-cloud <env> migrate-couchdb myplan.yml clean
```
