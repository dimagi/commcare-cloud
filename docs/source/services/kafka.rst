Kafka
=====

.. contents:: Table of Contents
    :depth: 2

`https://kafka.apache.org/: <https://kafka.apache.org/>`_ Kafka is used for building real-time data pipelines and streaming apps.
It is horizontally scalable, fault-tolerant and wicked fast.
Kafka is used by CommCare to provide stream processing capabilities for data changes. Changes to certain
data models, such as cases and forms, are written to Kafka. Separate processes then read the changes
from Kafka and process (pillows) them into Elasticsearch or other secondary databases.

---------
Resources
---------

* `Upgrade guide <upgrading-kafka>`_
* `Command line tools <https://cwiki.apache.org/confluence/display/KAFKA/Replication+tools>`_

------------
Dependancies
------------


* Java
* Zookeeper

-----
Setup
-----

Kafka is installed on each host in the *kafka* inventory group and Zookeeper is installed on each
host in the *Zookeeper* inventory group.

---------------------
Expanding the cluster
---------------------


#. 
   Add new host to the inventory and install Kafka

   .. code-block::

      $ commcare-cloud <env> deploy-stack --limit=<new kafka host>

#. 
   Update localsettings

   .. code-block::

      $ commcare-cloud <env> update-config

#. 
   Move partitions to new node

Follow the steps outlined `below <#move-partitions>`_.

---------------
Useful commands
---------------

All of the command below assume they are being run from the ``/opt/kafka/bin/`` path.

Show topic configuration
^^^^^^^^^^^^^^^^^^^^^^^^
**Note**\ : Use below command when the ``kafka version is < 3.x``. The ``--zookeeper`` argument is removed from 3.x.

   .. code-block::

      $ ./kafka-topics.sh --describe --zookeeper=<zookeeper host>:2181 --topic <topic>

**Note**\ : Use below command when the ``kafka version is >= 3.x``.

   .. code-block::

      $ ./kafka-topics.sh --describe --bootstrap-server=<kafka host>:9092 --topic <topic>

Add new partitions to topic
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**N** is the total number of partitions the topic should have

**Note**\ : Use below command when the ``kafka version is < 3.x``. The ``--zookeeper`` argument is removed from 3.x.

   .. code-block::

      $ ./kafka-topics.sh --alter --zookeeper=<zookeeper host>:2181 --topic <topci> --partitions N

**Note**\ : Use below command when the ``kafka version is >= 3.x``.

   .. code-block::

      $ ./kafka-topics.sh --alter --bootstrap-server=<kafka host>:9092 --topic <topci> --partitions N

**Note**\ : Adding partitions to a topic should be done in conjunction with updating the CommCare
Pillowtop process configurations as described in the `CommCare docs <https://commcare-hq.readthedocs.io/pillows.html#parallel-processors>`_.

Move partitions
^^^^^^^^^^^^^^^

**NOTE**\ : This can be done while all services are online


#. 
   Create the list of topics to rebalance

   .. code-block::

       $ cat topics.json
       {
         "topics": [{"topic": "case-sql"},{"topic": "form-sql"}],
         "version": 1
       }

#. 
   Generate the reassignments

**Note**\ : Use below command when the ``kafka version is < 3.x``. The ``--zookeeper`` argument is removed from 3.x.

   .. code-block::

       $ /opt/kafka/bin/kafka-reassign-partitions.sh --zookeeper=localhost:2181 --broker-list "0,1,2" --topics-to-move-json-file topics.json --generate 

**Note**\ : Use below command when the ``kafka version is >= 3.x``.

   .. code-block::

       $ /opt/kafka/bin/kafka-reassign-partitions.sh --bootstrap-server=localhost:9092 --broker-list "0,1,2" --topics-to-move-json-file topics.json --generate 

**Output**:

   .. code-block::

       Current partition replica assignment

       {"version":1,"partitions":[{"topic":"case-sql","partition":96,"replicas":[0]}, ... ]}
       
       Proposed partition reassignment configuration

       {"version":1,"partitions":[{"topic":"case-sql","partition":96,"replicas":[1]}, ... ]}

**Note:** --broker-list: list of brokers that can have partitions assigned to them

#. 
   Copy the proposed reassignment configuration to a JSON file and verify / update as required

    ``replicas`` refers to the broker IDs that the partition should appear on. In the example
    below this will put the ``("case", 0)`` partition on broker 0 (with no replicas).

   .. code-block::

       $ cat partitions-to-move.json
       {
         "version":1,
         "partitions":[
           {"topic":"case","partition":0,"replicas":[0]},
           ...
         ]
       }

#. 
   Reassign the partitions and verify the change:

**Note**\ : Use below command when the ``kafka version is < 3.x``. The ``--zookeeper`` argument is removed from 3.x.

   .. code-block::

       $ ./kafka-reassign-partitions.sh --zookeeper=localhost:2181 --reassignment-json-file partitions-to-move.json --execute

       $ ./kafka-reassign-partitions.sh --zookeeper=localhost:2181 --reassignment-json-file partitions-to-move.json --verify

**Note**\ : Use below command when the ``kafka version is >= 3.x``.

   .. code-block::

       $ ./kafka-reassign-partitions.sh --bootstrap-server=localhost:9092 --reassignment-json-file partitions-to-move.json --execute

       $ ./kafka-reassign-partitions.sh --bootstrap-server=localhost:9092 --reassignment-json-file partitions-to-move.json --verify

See https://kafka.apache.org/documentation.html#basic_ops_cluster_expansion for more details.


Replication
^^^^^^^^^^^

For setting up the replication on existing topic we make use of a helper script which has the following capabilities:


* increase replication for existing topics
* decrease replication factor for existing topics
* remove all replicas from a particular broker so it can be decomissioned
* balance leaders

For details on how to use this tool please see `kafka-reassign-tool <https://github.com/dimas/kafka-reassign-tool>`_

---------------
Upgrading Kafka
---------------
   .. code-block::

      KAFKA-VERSION: Version of Kafka being upgraded to
      KAFKA-SCALA-VERSION: Version required by KAFKA-VERSION ( Can be found `here <https://kafka.apache.org/downloads>`_) .
      KAFKA_INTER_BROKER_PROTOCOL_VERSION: Maps to Kafka's inter.broker.protocol.version. If you have a cluster that runs brokers with different Kafka versions make sure they communicate with the same protocol version.
      KAFKA_LOG_MESSAGE_FORMAT_VERSION: Maps to Kafka's log.message.format.version. Specifies the protocol version with which your cluster communicates with its consumers.

Refer to `Kafka Upgrade documentation <https://kafka.apache.org/documentation/#upgrade>`_ for more details.


#. 
   Ensure that the Kafka config is up to date

   .. code-block::

       $ cchq <env> ap deploy_kafka.yml

#. 
   Update the Kafka version number and Scala version in ``public.yml``. For right Scala version please refer the `Kafka documentation <https://kafka.apache.org/downloads>`.

    **environments/\ `<env>`\ /public.yml**

   .. code-block::

       kafka_version: <KAFKA-VERSION> 
       kafka_scala_version: <KAFKA-SCALA-VERSION>

#. 
   Upgrade the Kafka binaries and config

   .. code-block::

       $ cchq <env> ap deploy_kafka.yml

#. 
   Upgrade the brokers one at a time Once you have done so, the brokers will be running the latest version   and you can verify that the cluster's behavior and performance meets expectations. It is still possible to downgrade at this point if there are any problems.

#. 
   Update Kafka config:

    **environments/\ `<env>`\ /public.yml**

   .. code-block::

       kafka_inter_broker_protocol_version: <KAFKA_INTER_BROKER_PROTOCOL_VERSION> 

   .. code-block::

       $ cchq <env> ap deploy_kafka.yml

#. 
   Update Kafka config (again):

    **environments/\ `<env>`\ /public.yml**

   .. code-block::

       kafka_log_message_format_version: <KAFKA_LOG_MESSAGE_FORMAT_VERSION>

   .. code-block::

       $ cchq <env> ap deploy_kafka.yml
