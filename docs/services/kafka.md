# Kafka

[https://kafka.apache.org/:](https://kafka.apache.org/)
>Kafka® is used for building real-time data pipelines and streaming apps. It is horizontally scalable,
fault-tolerant and wicked fast.

Kafka is used by CommCare to provide stream processing capabilities for data changes. Changes to certain
data models, such as cases and forms, are written to Kafka. Separate processes then read the changes
from Kafka and process (pillows) them into Elasticsearch or other secondary databases.

## Resources

* [Upgrade guide](kafka/upgrade.md)
* [Command line tools](https://cwiki.apache.org/confluence/display/KAFKA/Replication+tools)

## Dependancies
* Java
* Zookeeper

## Setup

Kafka is installed on each host in the *kafka* inventory group and Zookeeper is installed on each
host in the *Zookeeper* inventory group.

## Expanding the cluster

1. Add new host to the inventory and install Kafka
```
$ commcare-cloud <env> deploy-stack --limit=<new kafka host>
```

2. Update localsettings
```
$ commcare-cloud <env> update-config
```

3. Move partitions to new node

Follow the steps outlined [below](#move-partitions).

## Useful commands
All of the command below assume they are being run from the `/opt/kafka/bin/` path.

### Show topic configuration
```
$ ./kafka-topics.sh --describe --zookeeper=<zookeeper host>:2181 --topic <topic>
```

### Add new partitions to topic
**N** is the total number of partitions the topic should have
```
$ ./kafka-topics.sh --alter --zookeeper=<zookeeper host>:2181 --topic <topci> --partitions N
```

**Note**: Adding partitions to a topic should be done in conjunction with updating the CommCare
Pillowtop process configurations as described in the [CommCare docs](https://commcare-hq.readthedocs.io/pillows.html#parallel-processors).

### Move partitions
**NOTE**: This can be done while all services are online

1. Create the list of topics to rebalance

    ```
    $ cat topics.json
    {
      "topics": [{"topic": "case-sql"},{"topic": "form-sql"}],
      "version": 1
    }
    ```

2. Generate the reassignments

    ```
    $ /opt/kafka/bin/kafka-reassign-partitions.sh --zookeeper=localhost:2181 --broker-list "0,1,2" --topics-to-move-json-file topics.json --generate 
    Current partition replica assignment

    {"version":1,"partitions":[{"topic":"case-sql","partition":96,"replicas":[0]}, ... ]}
    Proposed partition reassignment configuration

    {"version":1,"partitions":[{"topic":"case-sql","partition":96,"replicas":[1]}, ... ]}
    ```

    --broker-list: list of brokers that can have partitions assigned to them

3. Copy the proposed reassignment configuration to a JSON file and verify / update as required

    `replicas` refers to the broker IDs that the partition should appear on. In the example
    below this will put the `("case", 0)` partition on broker 0 (with no replicas).
    ```
    $ cat partitions-to-move.json
    {
      "version":1,
      "partitions":[
        {"topic":"case","partition":0,"replicas":[0]},
        ...
      ]
    }
    ```

4. Reassign the partitions and verify the change:
    ```
    $ ./kafka-reassign-partitions.sh --zookeeper=localhost:2181 --reassignment-json-file partitions-to-move.json --execute
    
    $ ./kafka-reassign-partitions.sh --zookeeper=localhost:2181 --reassignment-json-file partitions-to-move.json --verify
    ```

See https://kafka.apache.org/documentation.html#basic_ops_cluster_expansion for more details.

### Replication
For setting up the replication on existing topic we make use of a helper script which has the following capabilities:
* increase replication for existing topics
* decrease replication factor for existing topics
* remove all replicas from a particular broker so it can be decomissioned
* balance leaders

For details on how to use this tool please see [kafka-reassign-tool](https://github.com/dimas/kafka-reassign-tool)

