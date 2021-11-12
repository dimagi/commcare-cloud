
Add a new celery machine into existing cluster
==============================================

Setup the new node
------------------

.. code-block::

   diff environments/<env>/inventory.ini
   + [celeryN]
   + <node ip>

.. code-block::

   diff environments/<env>/app_process.yml
   +   'celery11':
   +    reminder_case_update_queue:
   +      pooling: gevent
   +      concurrency: <int>
   +      num_workers: <int>

Configure
---------


#. Configure Shared Directory

.. code-block::

   commcare-cloud <env> ap deploy_shared_dir.yml --tags=nfs --limit=shared_dir_host


#. Deploy new node

.. code-block::

   commcare-cloud <env> deploy_stack.yml --limit=celeryN

Update Configs
--------------

.. code-block::

   commcare-cloud <env> update-config

Deploy code
-----------

.. code-block::

   cchq <env> deploy

Update supervisor config
------------------------

.. code-block::

   cchq <env> update-supervisor-confs
