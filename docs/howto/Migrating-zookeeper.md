### Migrating zookeeper to a new node.
This doc will explain how to migrate a running zookeeper to a new node without any downtime. First we will run ZooKeeper in replicated mode and shut down the primary server after that the secondary server will take over.

1. Add the new node in zookeeper group and run deploy-stack
```
cchq <env> deploy-stack --limit=<zookeeper node> 
```
2. Edit conf `/etc/zookeeper/conf/zoo.cfg` on both the nodes
```
server.1=zookeeper node1 IP:2888:3888
server.2=zookeeper node2 IP:2888:3888
```
Also edit `/var/lib/zookeeper/myid` to give each one an ID. (for ex 1 and 2 ) and restart the zookeeper.

3. Check if replication is working on both zookeeper node.
```
$ echo dump | nc localhost 2181 | grep brokers
```
You should see same output on both the server.

4. Remove the old zookeeper node from zookeeper group and run deploy-stack again to update all the kafka server to connect with new zookeeper node.
```
$ cchq <env> deploy-stack --limit=<All kafka nodes> --tags=kafka,zookeeper
```
5. Shutdown the old zookeeper node.

6. Remove the old node entry from  `/etc/zookeeper/conf/zoo.cfg` on new zookeeper nodes and restart the zookeeper service.

