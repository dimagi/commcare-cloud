
Setup Sentry self hosting
^^^^^^^^^^^^^^^^^^^^^^^^^

Running sentry on self hosting requires following minimuim services to be running


* Postgresql
* Redis
* Kafka
* zookeeper
* Snuba 
* Clickhouse server
* Sentry

How to setup
~~~~~~~~~~~~


#. Add a server to ``sentry`` and give it a var ``kafka_broker_id``
#. Setup following vars in ``public.yml``
   .. code-block::

      sentry_dbuser: 
      sentry_dbpassword:
      sentry_database: 
      sentry_system_secret_key:
      clickhouse_data_dir: 
      default_sentry_from_email:

#. Add the database and host detail inside ``postgresql.yml``
#. Run following command
   .. code-block::

      $ cchq <env> ap deploy_sentry.yml --limit=<sentry_hostname>

#. After the command is finished, ssh into sentry server, activate the sentry virtualenv and create a superuser for it.
   .. code-block::

      (sentry_app) root@MUMGCCWCDPRDRDV01:/home/sentry/sentry_app# sentry --config /home/sentry/config/ createuser
      Email: test@test.com
      Password: 
      Repeat for confirmation: 
      Should this user be a superuser? [y/N]: y
      User created: test@test.com
      Added to organization: sentry

#. Login to the sentry UI and now this admin account can be used to manage the sentry.
