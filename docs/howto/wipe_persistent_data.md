How To Wipe Persistent Data
===========================

1. Wipe BlobDB, ES, Couch using management commands.

       $ cchq monolith django-manage wipe_blobdb --commit
       $ cchq monolith django-manage wipe_es --commit
       $ cchq monolith django-manage delete_couch_dbs --commit

2. Prepend "wipe_environment_enabled: True" to public.yml (because it
   is easier to spot if it's prepended than appended).

       $ printf '%s\n%s\n' "wipe_environment_enabled: True" \
         "$(cat ~/environments/monolith/public.yml)" \
         > ~/environments/monolith/public.yml

3. Stop CommCare and close Postgres sessions.

       $ cchq monolith service commcare stop
       $ cchq monolith service postgresql stop
       $ cchq monolith service postgresql status

   If that doesn't stop Postgres and PgBouncer, and if Postgres is
   running on the same machine as you are logged in on, you can call
   `service` directly:

       $ sudo service pgbouncer stop
       $ sudo service postgresql stop
       $ sudo service postgresql start
       $ sudo service pgbouncer start

4. Wipe PostgreSQL databases

       $ cchq monolith ap wipe_postgres.yml

5. Wipe Kafka topics

       $ cchq monolith ap wipe_kafka.yml

   You can check they have been removed by confirming that
   "__consumer_offsets" is the only topic remaining:

       $ kafka-topics.sh --zookeeper localhost:2181 --list
       __consumer_offsets


Rebuilding environment
----------------------

1. Drop the first line public.yml. This step assumes the first line is
   "wipe_environment_enabled: True", prepended in the steps above.

       $ tail -n +2 ~/environments/monolith/public.yml > public.yml.tmp
       $ mv public.yml.tmp ~/environments/monolith/public.yml

2. Run Ansible playbook to recreate databases

       $ cchq monolith ap deploy_db.yml

3. Run management commands to create Kafka topics, create Postgres
   tables, and Elasticsearch indices.

       $ cchq monolith django-manage create_kafka_topics
       $ cchq monolith django-manage preindex_everything
       $ cchq monolith django-manage ptop_es_manage --flip_all_aliases
       $ cchq monolith django-manage check_services
       $ sudo -iu cchq  # Required to set CCHQ_IS_FRESH_INSTALL=1
       (cchq) $ cd www/monolith/current
       (cchq) $ source python_env-3.6/bin/activate
       (cchq) $ env CCHQ_IS_FRESH_INSTALL=1 ./manage.py migrate_multi
       (cchq) $ exit

4. Recreate a superuser (where you substitute your address in place of
   "you@your.domain").

       $ cchq monolith django-manage make_superuser you@your.domain
