.. role:: raw-html-m2r(raw)
   :format: html


Upgrading RabbitMQ
==================


* Current default RabbitMQ version: 3.6.15
* Example target version:3.8.5-1
  ## Dependency on Erlang Version
* Current default Erlang version: 20.2.2
* Example target version: 23.0.2 

Refer to `RabbitMQ Erlang Version Requirements <https://www.rabbitmq.com/which-erlang.html>`_ for more details.
Refer to `RabbitMQ Upgrade documentation <https://www.rabbitmq.com/upgrade.html#rabbitmq-cluster-configuration>`_ for more details.


#. 
   Ensure that the RabbitMQ  config is up to date

   .. code-block::

       $ cchq <env> ap deploy_rabbitmq.yml

#. 
   Update the RabbitMQ version number in ``public.yml``

    **environments/\ :raw-html-m2r:`<env>`\ /public.yml**

   .. code-block::

       rabbitmq_version: 3.8.5-1

#. 
   Update the Erlang version in ``main.yml``

   **src/commcare_cloud/ansible/roles/rabbitmq/defaults/main.yml**

   .. code-block::

      erlang: 1:23.0.2-2

#. 
   Full RabbitMQ Cluster downtime is required to upgrade from 3.6.15 to 3.8.5-1 version. 


#. 
   Export the current configuration backup using rabbitmqadmin or from rabbitmq console.

    **Download rabbitmqadmin command from "http://\ :raw-html-m2r:`<IP-of-RabbitMQ>`\ :15672/cli/"**

   .. code-block::

       $ rabbitmqadmin -u <usernamefromvault> -p <passwordfromvault> -U http://<IP-of-RabbitMQ>:15672 export rabbitmq-backup-config.json

#. 
   Stop the RabbitMQ service [ if in cluster then stop them in sequence] .

#. 
   Upgrade the RabbitMQ on the first node [ Upgrade the last node that was stopped first , if in cluster ]

#. 
   Update RabbitMQ :

   .. code-block::

       $ cchq <env> ap deploy_rabbitmq.yml

----

Alternative strategy: migrate to new RabbitMQ instance
------------------------------------------------------

If you want to do the migration with no downtime, another method is to set up a new rabbitmq machine
with the target version and gracefully drain the old one while directing traffic to the new one.


#. Set up the new machine using the normal process (make sure it's under [rabbitmq] in the inventory).
#. It will be important at each point in the transition to have a good read on where messages are going
    or accumulating. To do that, run
   .. code-block::

       (local) $ cchq production ssh ansible@<machine>
       (server) $ tmux
       (server|tmux) $ sudo watch "rabbitmqctl list_queues -p commcarehq name messages | grep -v '[^0-9]0$' | sort"
    in a tmux session on each machine (old and new).
#. Assuming you have multiple celery machines, pick some to be the "bridge" machines that
    will read from the old and write to the new, eventually draining them; the remaining machines will get
    all new traffic. In the inventory file, give each of these "bridge" celery machines the variable
   .. code-block::

       rabbitmq_migration_bridge=true

#. Edit public.yml to have
   .. code-block::

       AMQP_HOST: "{{ <new rabbitmq ip> }}"  # Maybe "{{ groups.rabbitmq.0 }}"
       OLD_AMQP_HOST: "{{ <old rabbitmq ip> }}"  # Maybe "{{ groups.rabbitmq.1 }}"
   and run
   .. code-block::

       cchq <env> update-config
   but don't restart services yet.
   Adding ``OLD_AMQP_HOST`` will make celery machines with ``rabbitmq_migration_bridge=true`` get different
   broker settings in ``localsettings.py`` that make it read from the old and write to the new rabbitmq. 
#. Check to make sure the connection to the new rabbitmq machine is working by running
   .. code-block::

       $ cchq production django-manage shell
       >>> from corehq.celery_monitoring.tasks import *
       >>> heartbeat__analytics_queue.delay()
    which will trigger a task and should write to the new machine. Check the tmux watch command you have running
    on the new machine to make sure a task went there.
#. Restart services with
   .. code-block::

       cchq <env> fab restart_services
    to pick up the changes from 4 & 5. All machines will now read from and write to the new machine,
    except for the "bridge celery machines" you chose, which will now read from the old and write to the new.
#. Watch the "watch" command on the old machine until all of the queues are fully drained. 
#. Finally (make sure you've removed the ``OLD_AMQP_HOST`` variable), run
   .. code-block::

       cchq <env> update-config
   You can leave ``rabbitmq_migration_bridge=true`` on the portion of celery machines you added it to
   for the next time, or you can remove it now. When ``OLD_AMQP_HOST`` is not set, it has no effect.
