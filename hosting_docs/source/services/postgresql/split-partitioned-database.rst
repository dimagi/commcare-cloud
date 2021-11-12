
Splitting a shard in postgresql
===============================

This document describes the process required to split a partitioned database
from one PostgreSQL instance into itself and another. This migration will
require downtime.

Assumptions
-----------

For the purposes of this document we'll assume that we have three database machines, *pg1*
, *pg2* and *pg3*. *pg1* has one database and *pg2* and *pg3* has none:

*pg1* databases:


* *commcarehq_p1* (with django alias *p1*\ )

*pg2* and *pg3* is a newly deployed server in the *[postgresql]* group and we want to
create a new  *commcarehq_p2* on *pg2*  and *commcarehq_p3* on *pg3* with half the data from *commcarehq_p1* on each.

*pg1* is currently the only database containing sharded data.
Half of the data should be moved to a new *pg2* and *pg3* servers

Current database configuration:

.. code-block:: python

   PARTITION_DATABASE_CONFIG = {
       'shards': {
           'p1': [0, 3],
       },
       'groups': {
           'main': ['default'],
           'proxy': ['proxy'],
           'form_processing': ['p1'],
       },
   }

   DATABASES = {
       'proxy': {
           'ENGINE': 'django.db.backends.postgresql_psycopg2',
           'NAME': 'commcarehq_proxy',
           'USER': 'commcarehq',
           'PASSWORD': 'commcarehq',
           'HOST': 'pg1',
           'PORT': '5432',
           'TEST': {
               'SERIALIZE': False,
           },
       },
       'p1': {
           'ENGINE': 'django.db.backends.postgresql_psycopg2',
           'NAME': 'commcarehq_p1',
           'USER': 'commcarehq',
           'PASSWORD': 'commcarehq',
           'HOST': 'pg1',
           'PORT': '5432',
           'TEST': {
               'SERIALIZE': False,
           },
       },
   }

At the end of this process shards 0 & 1 should be on *pg2* and shards 2 & 3 will be on *pg3*.

Important Notes
---------------

By default pglogical does not replicate any DDL commands.
This means that any CommCare HQ migrations may not be applied to the target databases while logical replication is active.
It is recommended to not deploy any changes during the time when splitting the database.
More technical information can be found at https://github.com/2ndQuadrant/pglogical/blob/REL2_x_STABLE/docs/README.md#ddl

Process Overview
----------------


#. Ensure that *pg1* is set to use logical replication
#. Setup *pg2* and *pg3* as a new database
#. Setup logical replication from pg1 to pg2 and pg3
#. Promote *pg2* and *pg3* to a master node
#. Update the applications configuration to go to *pg2* and *pg3*

Process detail
--------------

1. Setup logical replication on *pg1*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In your inventory file set the following vars for *pg1*\ :

.. code-block::

   [pg1]
   ...
   postgresql_wal_level = logical
   postgresql_max_worker_processes = 8
   postgresql_shared_preload_libraries = ["pglogical"]

Also ensure that your replication user has superuser privileges on all databases, in vault.yml:

.. code-block:: yaml

   POSTGRES_USERS:
     replication:
       username: 'foo'
       password: 'bar'
       role_attr_flags: 'LOGIN,REPLICATION,SUPERUSER'

In postgresql.yml:

.. code-block:: yaml

   postgresql_hba_entries:
     - contype: host
       users: foo
       netmask: 'pg2 ip address'
     - contype: host
       databases: replication
       users: foo
       netmask: 'pg2 ip address'
     - contype: host
       users: foo
       netmask: 'pg3 ip address'
     - contype: host
       databases: replication
       users: foo
       netmask: 'pg3 ip address'

Then deploy these settings to your databases:

.. code-block:: bash

   commcare-cloud <env> ap deploy_db.yml --limit=pg1,pg2,pg3

2. Setup *pg2* and *pg3*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setup *pg2* and *pg3* as you would another postgresql database in commcare-cloud.

In addition to normal setup, add the following to your ``postgresql.yml`` file:

.. code-block:: yaml

   dbs:
     logical:
       - name: commcarehq_p2
         host: pg2
         master_host: pg1
         master_db_name: commcarehq_p1
         replication_set: [0, 1]
       - name: commcarehq_p3
         host: pg3
         master_host: pg1
         master_db_name: commcarehq_p1
         replication_set: [2, 3]

Deploy this change to your databases using:

.. code-block:: bash

   commcare-cloud <env> ap setup_pg_logical_replication.yml

This will begin the replication process in the background which replicates one table at a time. To check the progress:

.. code-block:: bash

   ANSIBLE_DISPLAY_SKIPPED_HOSTS=False commcare-cloud <env> ap setup_pg_logical_replication.yml --tags=status

   TASK [All subscriber status] *****************
   ok: [pg2] => {
       "msg": [
           [
               {
                   "show_subscription_status": "(sub_name,initializing,provider_name,\"connection_string\",internal_pg_logical_name,{subscription},{all})"
               }
           ]
       ]
   }

In the above output ``initializing`` means that the database is copying from the original to the new database.
Once complete it will change to ``replicating``

3. Stop all DB requests
^^^^^^^^^^^^^^^^^^^^^^^

Once the databases are fully replicated and you are ready to switch to the new databases, bring the site down.

**Stop all CommCare processes**

.. code-block:: bash

   commcare-cloud <env> downtime start

**Stop pgbouncer**

.. code-block:: bash

   commcare-cloud <env> service postgresql stop --only pgbouncer --limit pg1,pg2,pg3

Verify that the replication is up to date by ensuring ``replay_location`` and ``sent_location`` are the same for each database:

.. code-block:: bash

   ANSIBLE_DISPLAY_SKIPPED_HOSTS=False commcare-cloud <env> ap setup_pg_logical_replication.yml --tags=status --limit=pg1
   ok: [100.71.184.26] => {
       "msg": [
           [
               {
                   "application_name": "commcarehq_p2_0_1_sub",
                   "replay_location": "2058/4C93E6B0",
                   "sent_location": "2058/4C93E6B0"
               }
           ],
           [
               {
                   "application_name": "commcarehq_p3_2_3_sub",
                   "replay_location": "2058/4C93E6B0",
                   "sent_location": "2058/4C93E6B0"
               }
           ]
       ]
   }

Synchronize the sequences:

.. code-block:: bash

   ANSIBLE_DISPLAY_SKIPPED_HOSTS=False commcare-cloud <env> ap setup_pg_logical_replication.yml --tags=synchronize_sequences --limit=pg1

4. Update configuration
^^^^^^^^^^^^^^^^^^^^^^^

**Update ansible config**

Update the *dbs* variable in the environment's *postgresql.yml* file
to show that the *p2* database is now on *pg2*\ :

.. code-block:: diff

   ...
    dbs:
    ...
      form_processing:
        ...
        partitions:
   -      p1:
   -        shards: [0, 3]
   -        host: pg1
   +      p2:
   +        shards: [0, 1]
   +        host: pg2
   +      p3:
   +        shards: [2, 3]
   +        host: pg3
          ...

**Deploy changes**

.. code-block::

   # update localsettings
   commcare-cloud <env> update-config

   # update PostgreSQL config on new PG node
   commcare-cloud <env> ap deploy_db.yml --limit=pg2,pg3

   # update the pl_proxy cluster
   commcare-cloud <env> django-manage --tmux configure_pl_proxy_cluster

To remove the logical replication run the following on all subscriber databases:

.. code-block:: sql

   SELECT pglogical.drop_node(sub_name, true)

5. Restart services
^^^^^^^^^^^^^^^^^^^

**start pgbouncer**

.. code-block:: bash

   commcare-cloud <env> service postgresql start --only pgbouncer --limit pg2,pg3

**Restart services**

.. code-block:: bash

   commcare-cloud <env> downtime end

----

`︎⬅︎ PostgreSQL <../postgresql.md>`_ | `︎⬅︎ Overview <../..>`_
