How To Rebuild a CommCare HQ environment
========================================

These steps delete *all* CommCare data in your environment.

In practice, you will likely *only* need this to delete test environments. We strongly discourage using any of
these of steps on production data. Please fully understand this before proceeding as this will permenantly
delete all of your data.

Prior to Wiping Data
--------------------

#. Ensure CommCare services are in a healthy state. If you observe any issues, see the Troubleshooting section below.

   .. code-block::

      $ cchq <env_name> django-manage check_services


#. If planning to migrate data, deploy CommCare from a specific revision

   .. code-block::

      $ cchq <env_name> deploy commcare --commcare-rev=<commit-hash>

   .. note::
        You should have been given a commit hash that matches the revision of CommCare used to generate your
        exported data, and it is critical that this same CommCare revision is used to rebuild the new environment,
        and load data in. Please request a commit hash if you were not provided one.

#. Stop CommCare services to prevent background processes from writing to databases.

   .. code-block::

      $ cchq <env_name> downtime start
      # Choose option to kill any running processes when prompted

How To Wipe Persistent Data
---------------------------

These steps are intended to be run in the sequence given below, so you shouldn't proceed to next step until
the prior step is completed.

#. Ensure CommCare services are stopped to prevent background processes from writing to databases. 

   .. code-block::
     
      $ cchq <env_name> service commcare status

#. Add "wipe_environment_enabled: True" to `public.yml` file.

#. Wipe BlobDB, Elasticsearch, and Couch using management commands.

   .. code-block::

      $ cchq <env_name> django-manage wipe_blobdb --commit
      $ cchq <env_name> django-manage wipe_es --commit
      $ cchq <env_name> django-manage delete_couch_dbs --commit


#. Wipe PostgreSQL data (restart first to kill any existing connections)

   .. code-block::

      $ cchq <env_name> service postgresql restart
      $ cchq <env_name> ap wipe_postgres.yml

#. Clear the Redis cache data

   .. code-block::

      $ cchq <env_name> django-manage flush_caches

#. Wipe Kafka topics

   .. code-block::

      $ cchq <env_name> ap wipe_kafka.yml

#. Remove the "wipe_environment_enabled: True" line in your `public.yml` file.


Rebuilding environment
----------------------

#. Recreate all databases

   .. code-block::

      $ cchq <env_name> ap deploy_db.yml --skip-check

#. Run migrations for fresh install

   .. code-block::

      $ cchq <env_name> ap migrate_on_fresh_install.yml -e CCHQ_IS_FRESH_INSTALL=1

#. Create kafka topics
   
    .. code-block::

      $ cchq <env_name> django-manage create_kafka_topics

.. warning::

    If you are migrating a project to a new environment, return to the steps outlined in
    :ref:`import-data-into-environment`. Do not start services back up until you have finished loading
    data into your new environment.


Start new environment
---------------------

.. note::

   The following steps should only be run if you are **not** planning to migrate a project from an existing environment.


#. End downtime (you will encounter a prompt that says no record of downtime was found, continue anyway as this starts services up).

   .. code-block::

      $ cchq <env_name> downtime end


#. Recreate a superuser (where you substitute your address in place of
   "you@your.domain").

   .. code-block::

      $ cchq <env_name> django-manage make_superuser you@your.domain

Troubleshooting
---------------

Issues with check_services
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Kafka: No Brokers Available - Try resetting Zookeeper by performing the following steps:

  .. code-block::
    
     $ cchq monolith service kafka stop
     NOTE: The following paths may vary if you've specified different paths for ``kafka_data_dir`` and ``zookeeper_data_dir`` 
     $ rm -rf /var/lib/zookeeper/*
     $ rm -rf /opt/data/kafka/data/*
     $ cchq monolith service kafka restart
