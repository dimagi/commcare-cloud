
How To Wipe Persistent Data
===========================


#. 
   Wipe BlobDB, ES, Couch using management commands.

   .. code-block::

      $ cchq monolith django-manage wipe_blobdb --commit
      $ cchq monolith django-manage wipe_es --commit
      $ cchq monolith django-manage delete_couch_dbs --commit

#. 
   Prepend "wipe_environment_enabled: True" to public.yml (because it
   is easier to spot if it's prepended than appended).

   .. code-block::

      $ printf '%s\n%s\n' "wipe_environment_enabled: True" \
        "$(cat ~/environments/monolith/public.yml)" \
        > ~/environments/monolith/public.yml

#. 
   Stop CommCare and close Postgres sessions.

   .. code-block::

      $ cchq monolith service commcare stop
      $ cchq monolith service postgresql stop
      $ cchq monolith service postgresql status


   If that doesn't stop Postgres and PgBouncer, and if Postgres is
   running on the same machine as you are logged in on, you can call
   ``service`` directly:

   .. code-block::

      $ sudo service pgbouncer stop
      $ sudo service postgresql stop
      $ sudo service postgresql start
      $ sudo service pgbouncer start

#. 
   Wipe PostgreSQL databases

   .. code-block::

      $ cchq monolith ap wipe_postgres.yml

#. 
   Wipe Kafka topics

   .. code-block::

      $ cchq monolith ap wipe_kafka.yml


   You can check they have been removed by confirming that the following shows
   no output:

   .. code-block::

      $ kafka-topics.sh --zookeeper localhost:2181 --list

Rebuilding environment
----------------------


#. 
   Drop the first line public.yml. This step assumes the first line is
   "wipe_environment_enabled: True", prepended in the steps above.

   .. code-block::

      $ tail -n +2 ~/environments/monolith/public.yml > public.yml.tmp
      $ mv public.yml.tmp ~/environments/monolith/public.yml

#. 
   Run Ansible playbook to recreate databases

   .. code-block::

      $ cchq monolith ap deploy_db.yml

#. 
   Run management commands to create Kafka topics, create Postgres
   tables, and Elasticsearch indices.

   .. code-block::

      $ cchq monolith django-manage create_kafka_topics
      $ cchq monolith django-manage preindex_everything
      $ cchq monolith django-manage ptop_es_manage --flip_all_aliases
      $ cchq monolith django-manage check_services
      $ sudo -iu cchq  # Required to set CCHQ_IS_FRESH_INSTALL=1
      (cchq) $ cd www/monolith/current
      (cchq) $ source python_env/bin/activate
      (cchq) $ env CCHQ_IS_FRESH_INSTALL=1 ./manage.py migrate_multi
      (cchq) $ exit

#. 
   Recreate a superuser (where you substitute your address in place of
   "you@your.domain").

   .. code-block::

      $ cchq monolith django-manage make_superuser you@your.domain
