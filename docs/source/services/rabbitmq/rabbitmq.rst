
RabbitMQ
========

Usage in CommCare
-----------------

`RabbitMQ <https://www.rabbitmq.com/>`_ is a message broker which supports publish/subscribe workflows.
RabbitMQ groups exchanges, queues, and permissions into virtual hosts.
For our setup in production, the virtual host is always “commcarehq”. Locally you might be using the default virtual host of “/”.

Guides
------

* :ref:`services/rabbitmq/migrate-to-redis:Migrating from RabbitMQ to Redis as the Celery Broker`
* :ref:`services/rabbitmq/upgrade:Upgrading RabbitMQ`
