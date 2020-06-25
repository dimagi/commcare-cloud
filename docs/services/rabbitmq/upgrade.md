# Upgrading RabbitMQ 

* Current default RabbitMQ version: 3.6.15
* Example target version:3.8.5-1
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
    rabbitmq_version: 3.8.5-1
    ```
3. Update the Erlang version in `main.yml`

   **src/commcare_cloud/ansible/roles/rabbitmq/defaults/main.yml**
   ```
   erlang: 1:23.0.2-2
   ```

4. Full RabbitMQ Cluster downtime is required to upgrade from 3.6.15 to 3.8.5-1 version. 
   

5. Export the current configuration backup using rabbitmqadmin or from rabbitmq console.

    **Download rabbitmqadmin command from "http://<IP-of-RabbitMQ>:15672/cli/"**
    ```
    $ rabbitmqadmin -u <usernamefromvault> -p <passwordfromvault> -U http://<IP-of-RabbitMQ>:15672 export rabbitmq-backup-config.json
    ```

6. Stop the RabbitMQ service [ if in cluster then stop them in sequence] .

7. Upgrade the RabbitMQ on the first node [ Upgrade the last node that was stopped first , if in cluster ]

8. Update RabbitMQ :

    ```
    $ cchq <env> ap deploy_rabbitmq.yml
    ```
