
Migrating from RabbitMQ to Redis as the Celery Broker
=====================================================

.. note::

   Support for RabbitMQ as the Celery message broker is being removed from
   commcare-cloud. All environments must migrate to Redis before upgrading
   to the next release.

Does this apply to me?
----------------------

Check your ``<env>/public.yml`` for the ``BROKER_URL`` setting:

- If ``BROKER_URL`` starts with ``redis://`` — you are already using Redis
  and **do not need to do anything**.
- If ``BROKER_URL`` starts with ``amqp://`` or is not set — you are using
  RabbitMQ and must follow this migration guide.

Prerequisites
-------------

You will need a Redis instance to use as the broker. This can be:

- A dedicated Redis instance (recommended for larger production environments)
- An existing Redis instance on a separate database (db number)

.. important::

   The broker Redis instance should be separate from the Redis instance used
   for caching, since broker workloads have different characteristics.
   At a minimum, use a different Redis database number.


Migration steps
---------------

Follow the steps for your deployment topology:

- **Monolith:** See :ref:`monolith-migration`.
- **Cluster:** See :ref:`cluster-migration`.


.. _monolith-migration:

Monolith migration
------------------

The migration drains all messages from RabbitMQ before cutting over to Redis.
You will experience delays in async processing (celery) while messages are
being drained, but no messages will be dropped.

1. Update ``<env>/public.yml`` with the Redis broker configuration:

   .. code-block:: yaml

      REDIS_BROKER_DB: '0'
      REDIS_BROKER_HOST: '<redis_broker_host>'
      REDIS_BROKER_PORT: '6379'
      BROKER_URL: "redis://{{ REDIS_BROKER_HOST }}:{{ REDIS_BROKER_PORT }}/{{ REDIS_BROKER_DB }}"

2. Set ``celery_broker_migration=true`` in ``<env>/inventory.ini.j2``
   on the monolith's celery group, then regenerate the inventory file
   (``cchq <env> aws-fill-inventory``):

   .. code-block:: ini

      [celery:vars]
      celery_broker_migration=true

3. Apply changes and restart:

   .. code-block:: bash

      cchq <env> update-config
      cchq <env> update-supervisor-confs
      cchq <env> service commcare restart

   The monolith will now read tasks from RabbitMQ and write new tasks to
   Redis, effectively draining the old broker. However notably, new tasks
   written to Redis will not be read until you remove ``celery_broker_migration=true``.

4. Monitor RabbitMQ until all queues are empty (see :ref:`confirm-drained`).

5. Remove ``celery_broker_migration=true`` from ``<env>/inventory.ini.j2``
   and regenerate the inventory file (``cchq <env> aws-fill-inventory``).

6. Apply changes and restart again:

   .. code-block:: bash

      cchq <env> update-config
      cchq <env> update-supervisor-confs
      # Say Yes when asked to reload supervisor processes

7. Proceed to :ref:`post-migration-cleanup`.


.. _cluster-migration:

Cluster migration
-----------------

For multi-machine deployments, designate one celery machine as the "bridge"
to drain messages from RabbitMQ while other machines read from Redis. If you
only have one celery machine, it is fine to make that the "bridge" machine, but
you will experience delays in async processing (celery) while messages are
being drained.


Step 1: Configure the new broker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Update ``<env>/public.yml`` with the Redis broker configuration:

   .. code-block:: yaml

      REDIS_BROKER_DB: '0'
      REDIS_BROKER_HOST: '<redis_broker_host>'
      REDIS_BROKER_PORT: '6379'
      BROKER_URL: "redis://{{ REDIS_BROKER_HOST }}:{{ REDIS_BROKER_PORT }}/{{ REDIS_BROKER_DB }}"

   This overrides the default AMQP ``BROKER_URL`` with a Redis URL.

2. Choose one celery machine to act as a "bridge" machine. It will
   drain remaining messages from RabbitMQ while writing new messages to Redis.

   - You need one bridge machine consuming **all** queues.
   - (Optional) Have at least one other (non-bridge) machine also consuming all queues
     to keep up with new traffic.
   - (Optional) Avoid selecting the machine running Flower as a bridge machine, as
     Flower will not work properly in bridge mode.

3. Set ``celery_broker_migration=true`` on the bridge machine in
   ``<env>/inventory.ini.j2``, then regenerate the inventory file
   (``cchq <env> aws-fill-inventory``):

   .. code-block:: ini

      [<bridge_celery_machine>:vars]
      celery_broker_migration=true


Step 2: Apply changes in order
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply the configuration changes to machines in this order:

a. **Non-bridge celery machines** (skip if you only have one celery machine):

   .. code-block:: bash

      # Stop celery on non-bridge machines
      cchq <env> service celery stop --limit=<non_bridge_groups>

      # Update config
      cchq <env> update-config --limit=<non_bridge_groups>

      # Update supervisor confs (say No when asked to reload)
      cchq <env> update-supervisor-confs --limit=<non_bridge_groups>

      # Start celery
      cchq <env> service celery start --limit=<non_bridge_groups>

   .. note::

      For the celerybeat machine, you will also need to stop and start all
      management command processes:
      ``sudo supervisorctl stop commcare-hq-<env>-<command>``

b. **Non-celery CommCare services** (webworkers, pillowtop, proxy):

   .. code-block:: bash

      cchq <env> update-config --limit=webworkers,pillowtop,proxy
      cchq <env> update-supervisor-confs --limit=webworkers,pillowtop,proxy
      cchq <env> service commcare restart --limit=webworkers,pillowtop,proxy

c. **Bridge celery machines** (they will read from RabbitMQ, write to Redis):

   .. code-block:: bash

      cchq <env> service celery stop --limit=<bridge_groups>
      cchq <env> update-config --limit=<bridge_groups>
      cchq <env> update-supervisor-confs --limit=<bridge_groups>
      # Say No when asked to reload
      cchq <env> service celery start --limit=<bridge_groups>

   Verify that ``localsettings.py`` on bridge machines shows:

   - ``CELERY_BROKER_READ_URL`` pointing to the old RabbitMQ (``amqp://...``)
   - ``CELERY_BROKER_WRITE_URL`` pointing to the new Redis (``redis://...``)


Step 3: Confirm drained and cut over
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Monitor RabbitMQ until all queues are empty (see :ref:`confirm-drained`).

2. Remove ``celery_broker_migration=true`` from ``<env>/inventory.ini.j2``
   and regenerate the inventory file (``cchq <env> aws-fill-inventory``).

3. Apply changes to bridge machines. Note that active processes on bridge machines
   may not respond to ``service celery stop`` at this point, so ensure memory
   usage is below 50% before proceeding (processes will effectively double
   during the update):

   .. code-block:: bash

      cchq <env> update-config --limit=<bridge_machines>
      cchq <env> update-supervisor-confs --limit=<bridge_machines>
      # Say Yes when asked to reload supervisor processes

4. Proceed to :ref:`post-migration-cleanup`.


.. _confirm-drained:

Confirming RabbitMQ is drained
------------------------------

Monitor RabbitMQ until all queues have 0 messages:

.. code-block:: bash

   cchq <env> ssh rabbitmq
   sudo rabbitmqctl -p commcarehq list_queues name messages \
       | grep -vE 'pidbox' \
       | column -t

Exclude ``pidbox`` queues — those are used for worker communication and are
not relevant to the migration. Wait until all other queues show 0 messages.


.. _post-migration-cleanup:

Post-migration cleanup
----------------------

After confirming everything is working on Redis, clean up the remaining
RabbitMQ references from your environment configuration:

1. **Remove machines/groups from the** ``[rabbitmq]`` **inventory group** in
   ``<env>/inventory.ini.j2`` and regenerate the inventory file
   (``cchq <env> aws-fill-inventory``). For example, remove sections like:

   .. code-block:: ini

      [rabbitmq:children] <- keep this
      rabbitmq_host_group <- remove this line

2. **Remove RabbitMQ variables** from ``<env>/public.yml``:

   - ``AMQP_HOST``
   - ``OLD_AMQP_HOST``
   - ``OLD_AMQP_NAME``
   - ``rabbitmq_version``
   - ``erlang``
   - Any ``BROKER_URL`` still using ``amqp://``

3. **Remove AMQP secrets** from your vault file (``<env>/vault.yml``):

   - ``AMQP_USER``
   - ``AMQP_PASSWORD``
   - ``OLD_AMQP_USER`` (if present)
   - ``OLD_AMQP_PASSWORD`` (if present)

   Edit with: ``ansible-vault edit environments/<env>/vault.yml``

4. **Decommission the RabbitMQ server(s)** once you are confident the
   migration is complete and no rollback is needed.

Your final ``<env>/public.yml`` broker configuration should look like:

.. code-block:: yaml

   REDIS_BROKER_DB: '0'
   REDIS_BROKER_HOST: '<your_redis_broker_host>'
   REDIS_BROKER_PORT: '6379'
   BROKER_URL: "redis://{{ REDIS_BROKER_HOST }}:{{ REDIS_BROKER_PORT }}/{{ REDIS_BROKER_DB }}"


Getting help
------------

If you run into any issues during the migration, please reach out on the
`Developers section of the CommCare forum <https://forum.dimagi.com/c/developers/>`_.
