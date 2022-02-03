.. _migrate-instance:

Migrating an entire CommCareHQ instance
=======================================

This document describes high level steps to migrate an entire CommCareHQ instance from one set of servers
to another set of servers.  If you are looking to migrate just a single project to a new environment
please see :ref:`migrate-instance`. You can also use that method if you care about
only a single project in your environment and don't need other projects.

There are database and application services in a CommCareHQ instance. Only the data for database services need to be
migrated. There is no data to be migrated for stateless application services such as Django/Nginx/Celery/Pillow.
It is recommended that you understand the below high level steps, document necessary commands to be run prior
and plan out a migration timeline since it involves downtime. The downtime amount depends on how large your data size is.


#. Setup the new environment. Naming the environment with a new name and the servers with new host names is helpful down the line.
#. Disable automated tasks on new cluster (cron, monit, restarter scripts).
#. Start the downtime by stopping nginx and django services on old environment.
   You can use :code:`commcare-cloud service` command to do this.
#. Let the pillow/celery changes finish processing. This can be monitored using the monitoring dashboards.
#. Stop all the services and ensure that the databases are not getting any reads/writes.
#. Copy static site content from old to new nginx server. The data is in :code:`/etc/nginx/.htpasswd\*` and :code:`/var/www/html/`.
#. Migrate data from old machines to corresponding machines in the new environment.
	- Setup necessary SSH permissions to transfer data between old and new machines.
	- For Postgres/Elasticsearch/CouchDB, you can rsync the data directory for between corresponding nodes in old and new environments.
	- You may want to use :code:`commcare-cloud copy-files` command if you have large number of nodes.
	- Alternatively, data can be migrated using backups taken after the services have stopped.
	- For BlobDB, follow the migration steps depending on what software you are using to host BlobDB.
	- Update pl_proxy config using :code:`./manage.py configure_pl_proxy_cluster`.
	- Setup postgres standby nodes if you are using. You can use `setup_pg_standby playbook <https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/setup_pg_standby.yml>`_ to do this.
#. Deploy a code deploy on new environment.
#. Reset kafka checkpoints (for pillows) by doing `KafkaCheckpoint.objects.all().update(offset=0)` in a django management shell.
#. Perform a test to make sure the data in old and new environments match.
   - You can use `print_domain_stats` management command on both envs to compare.
   - Export forms or cases with few filters and compare.
#. Perform functionality tests using :ref:`new-env-qa` using a test domain.
#. Perform basic sync/submission tests on a CommCare mobile device. Since a DNS name is not setup yet, you might have to use `/etc/hosts` or proxy forwarding to point the mobile device to the new environment when using the web address. Or you can create a mobile app using `CUSTOM_APP_BASE_URL` pointing to the public IP of new environment.
#. If everything is good, you can flip the DNS of your website to the public address of the new environment.
#. Your monitoring dashboards should start registering requests coming to the new environment.
