# Add a new CouchDB node to an existing cluster

## Setup the new node and add it to the cluster
* Update inventory

```diff
  [couchN]
  <node ip>

  [couchdb2]
  ...
+ couchN
```

* Deploy new node

```
commcare-cloud <env> deploy_stack.yml --limit=couchN
```

* Add node to cluster

```
$ commcare-cloud <env> aps --tags=add_couch_nodes --limit=couchdb2
```
