# Upgrading Kafka

* Current default version: 0.8.2.2
* Example target version: 2.4.1

Refer to [Kafka Upgrade documentation](https://kafka.apache.org/documentation/#upgrade) for more details.

1. Ensure that the Kafka config is up to date

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```

2. Update the Kafka version number in `public.yml`

    **environments/<env>/public.yml**
    ```
    kafka_version: 2.4.1
    ```

3. Upgrade the Kafka binaries and config

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```

4. Validate that the system is still working

5. Update Kafka config:

    **environments/<env>/public.yml**
    ```
    kafka_inter_broker_protocol_version: 2.4
    ```

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```

6. Update Kafka config (again):

    **environments/<env>/public.yml**
    ```
    kafka_log_message_format_version: 2.4
    ```

    ```
    $ cchq <env> ap deploy_kafka.yml
    ```
