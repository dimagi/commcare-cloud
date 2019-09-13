# Kafka

[https://kafka.apache.org/:](https://kafka.apache.org/)
>Kafka® is used for building real-time data pipelines and streaming apps. It is horizontally scalable,
fault-tolerant and wicked fast.

Kafka is used by CommCare to provide stream processing capabilities for data changes. Changes to certain
data models, such as cases and forms, are written to Kafka. Separate processes then read the changes
from Kafka and process (pillows) them into Elasticsearch or other secondary databases.

## Resources

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

#### [kafka-reassign-tool](https://github.com/dimas/kafka-reassign-tool)

A helper script for Kafka to make it easier changing replicas for existing topics

`kafka-reassign-tool` uses Kafka's standard `kafka-reassign-partitions.sh` script and generates data for it.
The main purpose of this script is to make changing replication factor for existing topics easier.
`kafka-reassign-tool` simply generates partition reassignment JSON file that can be fed into `kafka-reassign-partitions.sh`
for execution.

What it can do:
* increase replication for existing topics
* decrease replication factor for existing topics
* remove all replicas from a particular broker so it can be decomissioned
* balance leaders

## Configuration
`kafka-reassign-tool` needs to know where Kafka standard scripts are located as well as Zookeeper URL.
If your Kafka is installed in `/opt/kafka` you do not need to supply any additional command line options. Otherwise you
need to provide `--kafka-home <dir>` command line option.
Either way the script will attempt to read zookeeper URL from `config/server.properties` of Kafka home directory.
If that does not work for any reason, you may need to add `--zookeeper <url>` option.

## Changing replication factor
Running the tool with `--replication-factor 3` for example will change partition assignment map so that each partition has 3 replicas in the end.
`kafka-reassign-tool` goes over all partitions one by one and:
* if partition has fewer replicas than needed - adds more replicas by selecting least used brokers (that have fewer replicas for the topic than others)
* if partition has more replicas than needed - removes extra replicas by removing most used brokers (that have more replicas for the topic than others)
* if partition already at target replication factor, the tool still may re-order its replicas to make sure leader distribution is more level among brokers

This is an example output of the tool when it is asked to increase replication factor for a topic with 2 replicas to 3:
```
$ kafka-reassign-tool --topic mytopic --replication-factor 3

Reading /opt/kafka/config/server.properties
Using zookeeper URL: localhost:2181/kafka
Reading list of brokers...
Reading list of topics...
------------------------
Brokers:
  1001
  1002
  1003
  1004
Topics:
  mytopic
------------------------
Getting current assignments...
Building new assignments...
  mytopic-0 : [1001, 1002] => [1001, 1002, 1003]
  mytopic-2 : [1002, 1004] => [1002, 1004, 1001]
  mytopic-1 : [1002, 1004] => [1002, 1003, 1004]
  mytopic-3 : [1003, 1001] => [1003, 1001, 1004]
Saving new assignments into new-assignments.json...
Done
```
And a similar ouptut when it is asked to decrease replication factor for a topic with 2 replicas to 1:
```
$ kafka-reassign-tool --topic mytopic --replication-factor 1

Reading /opt/kafka/config/server.properties
Using zookeeper URL: localhost:2181/kafka
Reading list of brokers...
Reading list of topics...
------------------------
Brokers:
  1001
  1002
  1003
  1004
Topics:
  mytopic
------------------------
Getting current assignments...
Building new assignments...
  mytopic-0 : [1001, 1002] => [1001]
  mytopic-2 : [1002, 1004] => [1002]
  mytopic-1 : [1002, 1004] => [1004]
  mytopic-3 : [1003, 1001] => [1003]
Saving new assignments into new-assignments.json...
Done
```

Of course, it always makes sense to eyeball what changes `kafka-reassign-tool` plans before actually executing them.

### Bulk change
You can supply `--topic` option multiple times:
```
$ kafka-reassign-tool --topic mytopic1 --topic mytopic2 --replication-factor 3
```
or you can omit it completely in which case the same replication factor will be applied to all topics in your cluster
```
$ kafka-reassign-tool --replication-factor 3
```
Which, of course, only makes sense when all your topics share the same replication factor

## Decomissioning a broker
The `--brokers` command line option allows you to specify which brokers can be used for assignment.
`kafka-reassign-tool` remove all assignments from brokers that are not in that list (replacing it with others to maintain replication factor).
This can be used to decomission a certain broker by removing all replicas from it.

For example, the command below does not list broker 1004 so if any partition used it as a replica, it will be changed to something else:
```
$ kafka-reassign-tool --topic mytopic --replication-factor 2 --brokers 1001,1002,1003

Reading /opt/kafka/config/server.properties
Using zookeeper URL: localhost:2181/kafka
Reading list of brokers...
Reading list of topics...
------------------------
Brokers:
  1001
  1002
  1003
  1004
Topics:
  mytopic
------------------------
Getting current assignments...
Building new assignments...
  mytopic-0 : [1001, 1002] => [1001, 1002]
  mytopic-2 : [1002, 1004] => [1002, 1003]
  mytopic-1 : [1002, 1004] => [1002, 1001]
  mytopic-3 : [1003, 1001] => [1003, 1001]
Saving new assignments into new-assignments.json...
Done
```

Note that this operation can also be used in bulk by providing multiple `--topic` options or omitting it completely to select all topics.
However, keep in mind that the same value from `--replication-factor` will be used for all selected topics.

## Applying the change
After successful invocation, `kafka-reassign-tool` generates `new-assignments.json` file which can be then applied as
```
kafka-reassign-partitions.sh --zookeeper <url> --reassignment-json-file new-assignments.json --execute --throttle 100000000
```
the example above throttles replication to 100Mb/sec. You may decide to use a different limit or to omit it completely.
If throttling was used, at the end you must verify reassignmnet with
```
kafka-reassign-partitions.sh --zookeeper <url> --reassignment-json-file new-assignments.json --verify
```
so replication quota is reset. For more details see https://kafka.apache.org/documentation.html#rep-throttle
