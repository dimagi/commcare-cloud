How To Rebuild a CommCare HQ environment
========================================

This step deletes all of the CommCare data from your environment and resets to as if it's a new environment.
In practice, you will likely need this only to delete test environments and not production data. Please understand fully
before you proceed to perform this as it will permenantly delete all of your data.


How To Wipe Persistent Data
---------------------------

This step deletes all of the persistent data in BlobDB, Postgres, Couch and Elasticsearch. Note that this works only 
in the sequence given below, so you shouldn't proceed to next steps until the prior steps are successful.


#. Wipe BlobDB, ES, Couch using management commands.

   .. code-block::

      $ cchq <env_name> django-manage wipe_blobdb --commit
      $ cchq <env_name> django-manage wipe_es --commit
      $ cchq <env_name> django-manage delete_couch_dbs --commit

#. Add "wipe_environment_enabled: True" to `public.yml` file.

#. Stop CommCare

   .. code-block::

      $ cchq <env_name> service commcare stop

#. Reset PostgreSQL and PgBouncer

   .. code-block::

      $ cchq <env_name> ap deploy_postgres.yml

#. Wipe PostgreSQL data

   Check status. Once status is "OK", wipe PostgreSQL data

   .. code-block::

      $ cchq <env_name> service postgresql status
      $ cchq <env_name> ap wipe_postgres.yml

#. Clear the Redis cache data

   .. code-block::

      $ cchq <env_name> django-manage flush_caches

#. Wipe Kafka topics

   .. code-block::

      $ cchq <env_name> ap wipe_kafka.yml


   You can check they have been removed by confirming that the following shows
   no output:

**Note**\ : Use below command when the ``kafka version is < 3.x``. The ``--zookeeper`` argument is removed from 3.x.

   .. code-block::

      $ kafka-topics.sh --zookeeper localhost:2181 --list

**Note**\ : Use below command when the ``kafka version is >= 3.x``.

   .. code-block::

      $  kafka-topics.sh --bootstrap-server localhost:9092 --list

Rebuilding environment
----------------------


#. Remove the "wipe_environment_enabled: True" line in your `public.yml` file.

#. Run Ansible playbook to recreate databases.

   .. code-block::

      $ cchq <env_name> ap deploy_db.yml --skip-check

   Run initial migration

   .. code-block::

      $ cchq <env_name> ap migrate_on_fresh_install.yml -e CCHQ_IS_FRESH_INSTALL=1

#. Run a code deploy to create Kafka topics and Elasticsearch indices.

   .. code-block::

      $ cchq <env_name> deploy


#. Recreate a superuser (where you substitute your address in place of
   "you@your.domain"). This is optional and should not be performed if
   you are planning to migrate domain from other environment.

   .. code-block::

      $ cchq <env_name> django-manage make_superuser you@your.domain
