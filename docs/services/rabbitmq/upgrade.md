# Upgrading RabbitMQ 

* Current default RabbitMQ version: 3.6.15
* Example target version:3.8.5
## Dependency on Erlang Version
* Current default Erlang version: 20.2.2
* Example target version: 23.0.2 

Refer to [RabbitMQ Erlang Version Requirements](https://www.rabbitmq.com/which-erlang.html) for more details.
Refer to [RabbitMQ Upgrade documentation](https://www.rabbitmq.com/upgrade.html#rabbitmq-cluster-configuration) for more details.

1. Ensure that the RabbitMQ  config is up to date

    ```
    $ cchq <env> ap deploy_rabbitmq.yml
    ```

2. Update the RabbitMQ version number in `public.yml`

    **environments/<env>/public.yml**
    ```
    rabbitmq_version: 3.8.5
    ```

3. Full RabbitMQ Cluster downtime is required to upgrade from 3.6.15 to 3.8.5 version. 

4. Export the current configuration backup using rabbitmqadmin or from rabbitmq console.

5. Stop the RabbitMQ service [ if in cluster then stop them in sequence] .

6. Upgrade the RabbitMQ on the first node [ Upgrade the last node that was stopped first , if in cluster ]

7. Update RabbitMQ :

    ```
    $ cchq <env> ap deploy_rabbitmq.yml
    ```
