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

----

## Alternative strategy: migrate to new RabbitMQ instance

If you want to do the migration with no downtime, another method is to set up a new rabbitmq machine
with the target version and gracefully drain the old one while directing traffic to the new one.

1. Set up the new machine using the normal process (make sure it's under [rabbitmq] in the inventory).
2. It will be important at each point in the transition to have a good read on where messages are going
    or accumulating. To do that, run
    ```
    (local) $ cchq production ssh ansible@<machine>
    (server) $ tmux
    (server|tmux) $ sudo watch "rabbitmqctl list_queues -p commcarehq name messages | grep -v '[^0-9]0$' | sort"
    ```
    in a tmux session on each machine (old and new).
3. Assuming you have multiple celery machines, pick some to be the "bridge" machines that
    will read from the old and write to the new, eventually draining them; the remaining machines will get
    all new traffic.
4. Make sure that the new machine comes first in inventory.ini, and then run
    ```
    cchq <env> update-config
    ```
    don't restart services yet.
5. Temporarily edit public.yml to have
    ```
    OLD_AMQP_HOST: "{{ <old rabbitmq ip> }}"
    ```
    but don't commit it. Then run
    ```
    cchq <env> update-config --limit <bridge celery machines>
    ```
   don't restart services yet.
6. Check to make sure the connection to the new rabbitmq machine is working by running
    ```
    $ cchq production django-manage shell
    >>> from corehq.celery_monitoring.tasks import *
    >>> heartbeat__analytics_queue.delay()
    ```
    which will trigger a task and should write to the new machine. Check the tmux watch command you have running
    on the new machine to make sure a task went there.
7. Restart services with
    ```
    cchq <env> fab restart_services
    ```
    to pick up the changes from 4 & 5. All machines will now read from and write to the new machine,
    except for the "bridge celery machines" you chose, which will now read from the old and write to the new.
8. Watch the "watch" command on the old machine until all of the queues are fully drained. 
9. Finally (make sure you've removed the OLD_AMQP_HOST variable), run
    ```
    cchq <env> update-config
    ```
    to bring the (former) bridge machines back into line with the rest of the machines.
    At this point all other machines are reading from and writing to the new rabbitmq machine,
    and you can stop the old one.
