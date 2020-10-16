# Upgrading Kafka

* Current default version: 2.4.1
* Example target version: 2.6.0

Refer to [Kafka Upgrade documentation](https://kafka.apache.org/documentation/#upgrade) for more details.

1. Ensure that the Kafka config is up to date

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```

2. Update the Kafka version number in `public.yml`

    **environments/<env>/public.yml**
    ```
    kafka_version: 2.6.0
    kafka_scala_version: 2.13
    ```

3. Upgrade the Kafka binaries and config

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```

4. Upgrade the brokers one at a time Once you have done so, the brokers will be running the latest version   and you can verify that the cluster's behavior and performance meets expectations. It is still possible to downgrade at this point if there are any problems.

5. Update Kafka config:

    **environments/<env>/public.yml**
    ```
    kafka_inter_broker_protocol_version: 2.6
    ```

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```

6. Update Kafka config (again):

    **environments/<env>/public.yml**
    ```
    kafka_log_message_format_version: 2.6
    ```

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```
