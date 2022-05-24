How To Rebuild a CommCareHQ environment
=======================================

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

   .. code-block::

      $ kafka-topics.sh --zookeeper localhost:2181 --list

Rebuilding environment
----------------------


#. Remove the "wipe_environment_enabled: True" line in your `public.yml` file.

#. Run Ansible playbook to recreate databases.

   .. code-block::

      $ cchq <env_name> ap deploy_db.yml --skip-check

#. Run a code deploy to create Kafka topics, create Postgres
   tables, and Elasticsearch indices.

   .. code-block::

      $ cchq <env_name> deploy


#. Recreate a superuser (where you substitute your address in place of
   "you@your.domain"). This is optional and should not be performed if
   you are planning to migrate domain from other environment.

   .. code-block::

      $ cchq <env_name> django-manage make_superuser you@your.domain
