# Redis Cluster

commcare-cloud supports setting up Redis as a monolith or as a cluster. Setting up monolith is simple and is in built in the full stack deploy. Simply add the host to `redis` host group in the inventory. Setting up a cluster is not fully automated in commcare-cloud and there are few additional steps required. This document explains how to setup Redis cluster.

## How to setup a Redis cluster

Redis requires at least three master nodes for a functional cluster. Read more on Redis cluster tutorial [documentation]([https://redis.io/topics/cluster-tutorial](https://redis.io/topics/cluster-tutorial)) to understand other requirements and limitations of Redis cluster. Redis cluster supports Redis master slave model, but commcare-cloud supports running Redis cluster with master nodes only. To setup Redis cluster using commcare-cloud, follow below steps

- Add Redis hosts under inventory groups `redis` and `redis_cluster_master`
- Run below to install Redis on the three nodes with cluster specific config
  ```
  commcare-cloud <env> deploy-stack --limit=<redis_hosts> --tags=redis
  ```
- On any one of the nodes, run below command to make the Redis hosts form a cluster with equal number of hash slots on each node (aka shards)
   ```
   /usr/local/src/redis-4.0.8/src/redis-trib.rb create --replicas 0 <list of redis URLs of all hosts in the format redis_ip:redis_port>
   ```

Note that this creates a fresh Redis cluster with no data. It is also possible to migrate an existing Redis monolith with data to a Redis cluster. This document doesn't go into details on that, but the general process involves below steps
- Setting up an empty redis cluster
- Resharding the cluster to have one node contain all hash slots instead of equal distribution
- Getting data dump from old Redis instance in aof or rdb format
- Restore the dump to the new node that has all slots
- Reshard the new cluster to equally distribute hash slots

## How to expand the cluster by adding a master node

Redis cluster can be expanded by adding more master nodes and resharding existing data. This can be done live while Redis cluster continues to serve requests, so a downtime may not be necessary. Below are the steps to expand a Redis cluster.

- Add the new Redis node under the host group `redis_cluster_master` and run below command to install Redis on this node
  ```
  commcare-cloud <env> deploy-stack --limit=<new_redis_host> --tags=redis
  ```
- Run below command  to add the node to the existing cluster. Run it on a redis host that is already part of the cluster 
   ```
  /usr/local/src/redis-4.0.8/src/redis-trib.rb add-node <new_redis_host:redis_port> <existing_redis_host_ip>:<redis_port>
  ```
- Run below command in a tmux to reshard the data which should take few minutes to complete.
```
./redis-trib.rb rebalance --use-empty-masters <existing_redis_host_ip>:<redis_port>
```

## How to migrate Redis cluster

Below process can be used to migrate redis cluster from one set of nodes to another set of nodes if they are all on the same VLAN.

The migration strategy involves adding new nodes to the existing cluster, pointing application to one of the new nodes, moving redis slots (aka  shard data) from old to new nodes and then removing the old nodes from the cluster.

Please read the whole section thouroughly before doing the migration.


- Setup the new redis nodes. This step can be done at any time before migration.
  `cchq icds deploy-stack --limit=new-redis-hosts --tags=redis --branch=<new-redis-hosts>`

- Add all new nodes to the old cluster one by one.
  ```
  cd /usr/local/src/redis-4.0.8/src/
  ./redis-trib.rb add-node <new_redis_host:redis_port> <any_old_redis_host_ip>:<redis_port>
  ```
  All `redis-trib.rb` commands can be run on any one of the nodes as long as absolute host addresses are used. Any one of the new nodes can be used.

- Run `update-config` from the new redis node branch, which should update `localsettings.REDIS_HOST` from the old redis node to new `redis_cluster_master[0]`

- Remove old nodes from the cluster one by one using below steps.
  - Move slots off of old node to equally redistribute to remaining nodes
    ```
    ./redis-trib.rb rebalance --use-empty-masters --weight <old_redis_node_ID>=0 <any_new_redis_host:redis_port>
    ```
    Redis node ID for a host can be found via `redis-cli CLUSTER NODES`

  - Delete the old node from cluster
    ```
    ./redis-trib.rb del-node <any_new_redis_host:redis_port> <old_redis_node_ID>
     ```
  - Make sure slots are redistributed as expected
    ```
    ./redis-trib.rb check <any_new_redis_host:redis_port>:6379
    ```

### General tips

- To verify that the key counts stay same before and after the migration, run
  ```
  cchq <env> run-shell-command <redis_hosts> 'redis-cli info | grep -A 2 Keyspace'
  ```
  This displays the number of keys on each redis node which should stay the same
- After the migration is finished it is best to turn off monit and redis on the old redis VMs and merge the branch into master to avoid someone doing an update-config on old master which will update `localsettings.REDIS_HOST` to the old Redis node (which will cause downtime).
- It's best to reshard redis nodes during non-peak load as sharding puts a slight memory stress on the nodes.