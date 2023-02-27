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


#. Stop CommCare and close Postgres sessions.

   .. code-block::

      $ cchq <env_name> service commcare stop
      $ cchq <env_name> service postgresql stop
      $ cchq <env_name> service postgresql status


   If that doesn't stop Postgres and PgBouncer, and if Postgres is
   running on the same machine as you are logged in on, you can call
   ``service`` directly:

   .. code-block::

      $ sudo service pgbouncer stop
      $ sudo service postgresql stop
      $ sudo service postgresql start
      $ sudo service pgbouncer start

#. Wipe PostgreSQL databases

   Check status & start postgres if NOT running.

   .. code-block::

      $ cchq <env_name> service postgresql status

   Status should be "OK" for both postgresql and pgbouncer.

   If not running, Start postgresql and pgbouncer through postgresql service

   .. code-block::

      $ cchq <env_name> service postgresql start

   If that does not start both successfully, reset services by running

   .. code-block::

      $ cchq <env_name> ap deploy_postgres.yml

   Check status & once status is "OK", Wipe postgres data

   .. code-block::

      $ cchq <env_name> ap wipe_postgres.yml

#. Clear the redis cache data

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
