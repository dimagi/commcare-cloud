.. _firefighting:

This is a firefighting guide to help troubleshoot various issues that might come up while running a CommCare HQ Server.

.. note::

  All Datadog links will be specific and private to Dimagi employees.
  If datadog releases a feature to share dashboard configurations, we will happily share configurations in this repository.

==================
Firefighting Guide
==================

.. contents:: Table of Contents
    :depth: 2


For a more user-friendly guide check out `Cory's brown bag on the topic <http://prezi.com/wedwm-dgqto7/firefighting-hq/>`_.


HQ Architecture and Machines
============================


.. image:: ./hq_architecture.png
   :target: ./hq_architecture.png
   :alt: 


High-level System Monitoring and Alerts
=======================================

`HQ Vitals <https://app.datadoghq.com/dashboard/g9s-pw6-tpg/hq-vitals?to_ts=1549314000000&is_auto=false&from_ts=1549227600000&live=true&tile_size=m&page=0>`_ - Various graphs on datadog

`Datadog Alerts <https://app.datadoghq.com/monitors/manage?q=status%3A(alert%20OR%20warn%20OR%20"no%20data">`_\ ) - these are also often reported on #hq-ops or #hq-ops-priority on slack

https://www.commcarehq.org/hq/admin/system/ - catchall system info, contains deploy history, pillowtop info, and a bunch of other stuff

https://www.commcarehq.org/hq/admin/system/check_services - plaintext URL that checks the status of a bunch of support services


Control machine log files
===================
There are two log files on the control machine that might be useful to reference if you need to know what commands were executed.
These files are located in the `/var/log/` directory and are:

- ansible.log: Shows the output of ansible commands.
- commands.log: Shows the commands that were run and by which user.


In case of a reboot
===================

After reboot, whether or not it was deliberate
----------------------------------------------

In case a machine has automatically rebooted or you needed to reboot a machine,
you will need to run the after-reboot protocol directly afterwards.
You can specify a single server by IP address, a single server by its name in inventory.ini.
You will have to confirm to run, and then provide the vault password for your environment.

.. code-block:: bash

   $ cchq <env> after-reboot [all|<group>|<server>]
   Do you want to apply without running the check first? [y/N]y

You don't always control the reboot process (sometimes our provider will expectedly or unexpectedly reboot a VM), but if you do, here's the process end to end:

.. code-block:: bash

   # Before shutting down VMs
   $ cchq <env> service commcare stop
   $ cchq <env> ansible-playbook stop_servers.yml

   # After restarting VMs
   $ cchq <env> after-reboot all
   $ cchq <env> django-manage check_services  # ping various auxiliary services to make sure they're up
     # if any services aren't running, you may have to manually start them:
   $ # cchq <env> service postgres start
   $ cchq <env> service commcare start  # start app processes

In case of network outage
=========================

If there has been a network outage in a cluster (e.g. firewall reboot), the following things should be checked to verify they are working:

Check services
--------------

.. code-block:: bash

   $ ./manage.py check_services
   # or go to
   https://[commcarehq.environment.path]/hq/admin/system/check_services

Check that change feeds are still processing
--------------------------------------------

You can use this graph on `datadog <https://app.datadoghq.com/dashboard/ewu-jyr-udt/change-feeds?to_ts=1549314000000&is_auto=false&live=true&from_ts=1549227600000&tile_size=m&page=0&fullscreen_widget=185100827>`_

Service Information
===================

Restarting services: ``cchq <env> service <service_name> restart``

Stopping services: ``cchq <env> service <service_name> stop``

Service logs: ``cchq <env> service <service_name> logs``

Datadog Dashboards
------------------

`postgres/pgbouncer <https://app.datadoghq.com/dash/263336/postgres---overview>`_

`redis <https://app.datadoghq.com/dash/290868/redis-timeboard>`_

`rabbitmq <https://app.datadoghq.com/screen/487480/rabbitmq---overview>`_

`pillow <https://app.datadoghq.com/dash/256236/change-feeds-pillows>`_

`celery/celerybeat <https://app.datadoghq.com/dash/141098/celery-overview>`_

`elasticsearch <https://app.datadoghq.com/screen/127236/es-overview>`_

`kafka <https://app.datadoghq.com/screen/516865/kafka---overview-cloned>`_

`Blob DB Dashboard <https://app.datadoghq.com/dashboard/753-35q-fwt/blob-db-dashboard>`_

`couch <https://app.datadoghq.com/screen/177642/couchdb-dashboard>`_

`formplayer <https://app.datadoghq.com/dashboard/dcs-kte-q8e/formplayer-health>`_

Switching to Maintenance Page
=============================

To switch to the Maintenance page, if you stop all web workers then the proxy will revert to "CommCare HQ is currently undergoing maintenance...".

.. code-block:: bash

   $ cchq <env> service webworker stop

To stop all supervisor processes use:

.. code-block:: bash

   $ cchq <env> service commcare stop

Couch 2.0
=========

Important note about CouchDB clusters. At Dimagi we run our CouchDB clusters with at least 3 nodes, and **store all data in triplicate**. That means if one node goes down (or even two nodes!), there are no user-facing effects with regards to data completeness so long as no traffic is being routed to the defective node or nodes. However, we have seen situations where internal replication failed to copy some documents to all nodes, causing views to intermittently return incorrect results when those documents were queried.

Thus in most cases, the correct approach is to stop routing traffic to the defective node, to stop it, and then to solve the issue with some better breathing room.

(If you do not store your data in duplicate or triplicate, than this does not apply to your cluster, and a single node being down means the database is either down or serving incomplete data.)

Couch node is down
------------------

If a couch node is down, the couch disk might be full. In that case, see `Couch node data disk is full <#couch-node-data-disk-is-full>`_ below. Otherwise, it could mean that the node is slow to respond, erroring frequently, or that the couch process or VM itself in a stopped state.

Monitors are setup to ping the proxy instead of couch instance directly, so the error will appear as "instance:http://\ :raw-html-m2r:`<proxy ip>`\ /\ *node/couchdb*\ :raw-html-m2r:`<couch node ip>`\ /".


#. log into couch node ip
#. service couchdb2 status
#. If it's not running start it and begin looking through log files (on the proxy, couch's files, maybe kernel or syslog files as well) to see if you can determine the cause of downtime
#. If it is running it could just be very slow at responding.
    a. Use fauxton to see if any tasks are running that could cause couch to become unresponsive (like large indexing tasks)
    b. It could also have ballooned (ICDS) which is out of our control
#. If it's unresponsive and it's out of our control to fix it at the time, go to the proxy machine and comment out the fault node from the nginx config. This will stop sending requests to that server, but it will continue to replicate. When the slowness is over you can uncomment this line and begin proxying reads to it again

Couch node data disk is high
----------------------------

Your best bet if the disk is around 80% is to compact large dbs.
If this happens regularly, you're probably better off adding more disk.

Log onto a machine that has access to couchdb:

.. code-block::

   cchq ${env} ssh django_manage

and then post to the _compact endpoints of the larger dbs, e.g.:

.. code-block::

   curl -X POST http://${couch_proxy}:25984/commcarehq__auditcare/_compact -v -u ${couch_username} -H 'Content-Type: application/json' -d'{}'
   curl -X POST http://${couch_proxy}:25984/commcarehq__receiverwrapper/_compact -v -u ${couch_username} -H 'Content-Type: application/json' -d'{}'

where ``${couch_proxy}`` is the address of the couchdb2_proxy machine (\ ``cchq ${env} lookup couchdb2_proxy``\ )
and ${couch_username} is the value of the ``COUCH_USERNAME`` secret (\ ``cchq ${env} secrets view COUCH_USERNAME``\ ).
You will also need to enter the value of the ``COUCH_PASSWORD`` secret (\ ``cchq ${env} secrets view COUCH_PASSWORD``\ ).

Couch node data disk is full
----------------------------

Stop routing data to the node
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If there is more than one couch node, and the other nodes are healthy, the fastest way to get to a calmer place is to pull the node with the full disk out of the proxy so requests stop getting routed to it. First


* Check that the other nodes do not have a full disk

To stop routing data to the node:


#. Comment it out under ``[couchdb2]`` in the ``inventory.ini``
#. Run
   .. code-block:: bash

       cchq <env> ansible-playbook deploy_couchdb2.yml --tags=proxy

#. Put the node in `maintenance mode <https://docs.couchdb.org/en/stable/cluster/sharding.html#set-the-target-node-to-true-maintenance-mode>`_.
#. Verify `internal replication is up to date <https://docs.couchdb.org/en/stable/cluster/sharding.html#monitor-internal-replication-to-ensure-up-to-date-shard-s>`_.
#. Stop its couchdb process
   .. code-block:: bash

       cchq production run-shell-command <node-name> 'monit stop couchdb2' -b

Increase its disk
^^^^^^^^^^^^^^^^^

The steps for this will differ depending on your hosting situation.

Link to internal Dimagi docs on `How to modify volume size on AWS <https://confluence.dimagi.com/display/internal/How+to+modify+volume+size+on+AWS>`_.

Once the disk is resized, couchdb should start normally. You may want to immediately investigate how to compact more aggressively to avoid the situation again, or to increase disk on the other nodes as well, since what happens on one is likely to happen on others sooner rather than later barring any other changes.

Add the node back
^^^^^^^^^^^^^^^^^

Once the node has enough disk


#. Start the node (or ensure that it's already started)
#. Force `internal replication <https://docs.couchdb.org/en/stable/cluster/sharding.html#forcing-synchronization-of-the-shard-s>`_.
#. Verify `internal replication is up to date <https://docs.couchdb.org/en/stable/cluster/sharding.html#monitor-internal-replication-to-ensure-up-to-date-shard-s>`_.
#. Clear node `maintenance mode <https://docs.couchdb.org/en/stable/cluster/sharding.html#clear-the-target-node-s-maintenance-mode>`_.
#. Reset your inventory.ini to the way it was (i.e. with the node present under the ``[couchdb2]`` group)
#. Run the same command again to now route a portion of traffic back to the node again:
   .. code-block:: bash

       cchq <env> ansible-playbook deploy_couchdb2.yml --tags=proxy

Compacting a shard
------------------

If a couch node is coming close to running out of space, it may not have enough space to compact the full db. You can start a compaction of one shard of a database using the following:

.. code-block::

   curl "<couch ip>:15986/shards%2F<shard range i.e. 20000000-3fffffff>%2F<database>.<The timestamp on the files of the database>/_compact" -X POST -H "Content-Type: application/json" --user <couch user name>

It's important to use port 15986. This is the couch node endpoint instead of the cluster. The only way to find the timstamp is to go into /opt/data/couchdb2/shards and look for the filename of the database you want to compact

If it's a global database (like _global_changes), then you may need to compact the entire database at once

.. code-block::

   curl "<couch ip>:15984/_global_changes/_compact" -X POST -H "Content-Type: application/json" --user <couch user name>

Documents are intermittently missing from views
-----------------------------------------------

This can happen if internal cluster replication fails. The precise causes are unknown at time of writing, but it has been observed after maintenance was performed on the cluster where at least one node was down for a long time or possibly when a node was stopped too soon after another node was brought back online after being stopped.

It is recommended to follow the `instructions above <#couch-node-data-disk-is-full>`_ (use maintenance mode and verify internal replication is up to date) when performing cluster maintenance to avoid this situation.

We have developed a few tools to find and repair documents that are missing on some nodes:

.. code-block:: sh

   # Get cluster info, including document counts per shard. Large persistent
   # discrepancies in document counts may indicate problems with internal
   # replication.
   commcare-cloud <env> couchdb-cluster-info --shard-counts [--database=...]

   # Count missing forms in a given date range (slow and non-authoritative). Run
   # against production cluster. Increase --min-tries value to increase confidence
   # of finding all missing ids.
   ./manage.py corrupt_couch count-missing forms --domain=... --range=2020-11-15..2020-11-18 --min-tries=40

   # Exhaustively and efficiently find missing documents for an (optional) range of
   # ids by running against stand-alone (non-clustered) couch nodes that have
   # snapshot copies of the data from a corrupt cluster. Multiple instances of this
   # command can be run simultaneously with different ranges.
   ./manage.py corrupt_couch_nodes NODE1_IP:PORT,NODE2_IP:PORT,NODE3_IP:PORT forms --range=1fffffff..3fffffff > ~/missing-forms-1fffffff..3fffffff.txt

   # Repair missing documents found with previous command
   ./manage.py corrupt_couch repair forms --min-tries=40 --missing ~/missing-forms-1fffffff..3fffffff.txt

   # See also
   commcare-cloud <env> couchdb-cluster-info --help
   ./manage.py corrupt_couch --help
   ./manage.py corrupt_couch_nodes --help

The process of setting up stand-alone nodes for ``corrupt_couch_nodes`` will
differ depending on the hosting environment and availability of snapshots/
backups. General steps once nodes are setup with snapshots of production data:


* Use a unique Erlang cookie on each node (set in ``/opt/couchdb/etc/vm.args``\ ).
  Do this before starting the couchdb service.
* Remove all nodes from the cluster except local node. The
  `couch_node_standalone_fix.py <https://gist.github.com/snopoke/f5c81497f6cbf3937dce2734e2b354a5>`_
  script can be used to do this.

DefaultChangeFeedPillow is millions of changes behind
-----------------------------------------------------

Background
^^^^^^^^^^

Most of our change feed processors (pillows) read from Kafka, but a small number of them serve
to copy changes from the CouchDB ``_changes`` feeds *into* Kafka,
the main such pillow being ``DefaultChangeFeedPillow``.
These pillows store as a checkpoint a CouchDB "seq", a long string that references a place
in the _changes feed. While these ``seq``\ s have the illusion of durability
(that is, if couch gives you one, then couch will remember it when you pass it back)
there are actually a number of situations in which CouchDB no longer recognizes a ``seq``
that it previously gave you. Two known examples of this are:


* If you have migrated to a different CouchDB instance using replication, it will *not*
    honor a ``seq`` that the old instance gave you.
* If you follow the proper steps for draining a node of shards (data) and then remove it,
    some ``seq``\ s may be lost. 

When couch receives a ``seq`` it doesn't recognize, it doesn't return an error.
Instead it gives you changes *starting at the beginning of time*.
This results in what we sometimes call a "rewind", when a couch change feed processor (pillow)
suddenly becomes millions of changes behind.

What to do
^^^^^^^^^^

If you encounter a pillow rewind, you can fix it by


* figuring out when the rewind happened,
* finding a recent CouchDB change ``seq`` from before the rewind happened, and
* resetting the pillow checkpoint to this "good" ``seq``

Figure out when the rewind happened
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Look at https://app.datadoghq.com/dashboard/ewu-jyr-udt/change-feeds-pillows for the right
environment, and look for a huge jump in needs_processed for DefaultChangeFeedPillow.

Find a recent ``seq``
~~~~~~~~~~~~~~~~~~~~~~~~~

Run

.. code-block::

   curl $couch/commcarehq/_changes?descending=true | grep '"1-"'

This will start at the latest change and go backwards, filtering for "1-" because
what we want to find is a doc that has only been touched once
(so we can easily reason with timestamps in the doc).
Start looking up the docs in couch by doc id,
until you find a doc with an early enough timestamp
(like a form with ``received_on``\ ). You're looking for a recent timestamp that happened
at a time *before* the rewind happened.

Reset the pillow checkpoint to this "good" seq
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run

.. code-block::

   cchq <env> django-manage shell --tmux

to get a live production shell on the ``django_manage`` machine,
and manually change the checkpoint using something like the following lines
(using the seq you found above instead, of course):

.. code-block::

   # in django shell
   seq = '131585621-g1AAAAKzeJzLYWBg4MhgTmEQTc4vTc5ISXIwNNAzMjDSMzHQMzQ2zQFKMyUyJMn___8_K4M5ieFXGmMuUIw9JdkkxdjEMoVBBFOfqTkuA40MwAYmKQDJJHu4mb_cwWamJZumpiaa49JKyFAHkKHxcEP31oMNNTJMSbIwSCbX0ASQofUwQ3_-uQI21MwkKcnYxAyfoVjCxdIcbGYeC5BkaABSQGPnQxw7yQZibpJpooGFGQ7dxBi7AGLsfrCxfxKPg401MDI2MzClxNgDEGPvQ1zrWwA2NsnCyCItLYkCYx9AjIUE7p8qSDIAutXQwMwAV5LMAgCrhbmz'
   from pillowtop.utils import get_pillow_by_name
   p = get_pillow_by_name('DefaultChangeFeedPillow')
   p.checkpoint.update_to(seq)

Nginx
=====

Occasionally a staging deploy fails because during a previous deploy, there was an issue uncommenting and re-commenting some lines in the nginx conf.

When this happens, deploy will fail saying

nginx: configuration file /etc/nginx/nginx.conf test failed
To fix, log into the proxy and su as root. Open the config and you'll see something like this

.. code-block::

   /etc/nginx/sites-enabled/staging_commcare
   #
   # Ansible managed, do not edit directly
   #

   upstream staging_commcare {
     zone staging_commcare 64k;

       least_conn;

   #server hqdjango0-staging.internal-va.commcarehq.org:9010;
   #server hqdjango1-staging.internal-va.commcarehq.org:9010;
   }

Ignore the top warning. Uncomment out the servers. Retsart nginx. Run restart_services.

NFS & File serving / downloads
==============================

For downloading files we let nginx serve the file instead of Django. To do this Django saves the data to a shared NFS drive which is accessible to the proxy server and then returns a response using the XSendfile/X-Accel-Redirect header which tells nginx to look for the file and serve it to the client directly.

The NFS drive is hosted by the DB machine e.g. hqdb0 and is located at /opt/shared_data (see ansible config for exact name). On all the client machines it is located at /mnt/shared_data (again see ansible config for exact name),

Troubleshooting
---------------

Reconnecting the NFS client
^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible that the mounted NFS folder on the client machines becomes disconnected from the host in which case you'll see errors like "Webpage not available"

To verify that this is the issue log into the proxy machine and check if there are any files in the shared data directories. If there are folders but no files then that is a good indication that the NFS connections has been lost. To re-establish the connection you should unmount and re-mount the drive:

.. code-block:: bash

   $ su
   $ umount -l /mnt/shared_data
   $ mount /mnt/shared_data
   # verify that it is mounted and that there are files in the subfolders

Forcing re-connection of an NFS client in a webworker (or other commcarehq machine)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It may happen, specially if the client crashes or has kernel oops, that a connection gets in a state where it cannot be broken nor re-established.  This is how we force re-connection in a webworker.


#. Verify NFS is actually stuck

   #. ``df`` doesn’t work, it hangs. Same goes for ``lsof``.
   #. ``umount`` results in ``umount.nfs: /mnt/shared_icds``\ : device is busy

#. top all app processes (gunicorn, etc) and datadog

   #. ``sudo supervisorctl stop all``
   #. ``sudo service datadog-agent stop``

#. Force umount 

   #. ``sudo umount -f /mnt/shared_icds``

      * if that doesn't work make sure to kill all app processes
        in e.g. for webworkers ``ps aux | grep gunicor[n]``

#. Re-mount

   #. ``sudo mount /mnt/shared_icds``
   #. Verify NFS mount works: ``df``

#. Start supervisor and app processes

   #. ``sudo service supervisord start``
   #. ``sudo supervisorctl start all``
   #. ``sudo service datadog-agent start``

If none of the above works check that nfsd is running on the shared_dir_host.

.. code-block:: bash

   $ ps aux | grep nfsd
   $ service nfs-kernel-server status

Pgbouncer
=========

We use pgbouncer as a connection pooler for PostgreSQL.

It is configured to use the "transaction"  pool mode which means that each server connection is assigned to client only during a transaction. When PgBouncer notices that transaction is over, the server will be put back into pool. This does have some limitations in terms of what the client can do in the connection e.g. no prepared statements. The full list of supported / unsupported operations is found on the pgboucer wiki.

Get a pgbouncer shell
---------------------

.. code-block::

   $ psql -U {commcarehq-user} -p 6432 pgbouncer

Check connection status
-----------------------

.. code-block::

   pgbouncer=# show pools;
     database  |      user      | cl_active | cl_waiting | sv_active | sv_idle | sv_used | sv_tested | sv_login | maxwait
   ------------+----------------+-----------+------------+-----------+---------+---------+-----------+----------+---------
    commcarehq | ************** |        29 |          0 |        29 |      10 |       8 |         0 |        0 |       0
    pgbouncer  | pgbouncer      |         1 |          0 |         0 |       0 |       0 |         0 |        0 |       0

   pgbouncer=# show clients;
    type |      user      |  database  | state  |      addr      | port  |  local_addr   | local_port |    connect_time     |    request_time     |    ptr    |   link
   ------+----------------+------------+--------+----------------+-------+---------------+------------+---------------------+---------------------+-----------+-----------
    C    | ************** | commcarehq | active | 10.209.128.58  | 39741 | 10.176.193.42 |       6432 | 2015-05-21 12:48:57 | 2015-05-21 13:44:07 | 0x1a59cd0 | 0x1a556c0
    C    | ************** | commcarehq | active | 10.209.128.58  | 40606 | 10.176.193.42 |       6432 | 2015-05-21 13:04:34 | 2015-05-21 13:04:34 | 0x1a668d0 | 0x1a6f590
    C    | ************** | commcarehq | active | 10.177.130.82  | 45471 | 10.176.193.42 |       6432 | 2015-05-21 13:17:04 | 2015-05-21 13:44:21 | 0x1a32038 | 0x1a8b060
    C    | ************** | commcarehq | active | 10.177.130.82  | 45614 | 10.176.193.42 |       6432 | 2015-05-21 13:17:23 | 2015-05-21 13:17:23 | 0x1a645a8 | 0x1a567a0
    C    | ************** | commcarehq | active | 10.177.130.82  | 45680 | 10.176.193.42 |       6432 | 2015-05-21 13:17:31 | 2015-05-21 13:44:21 | 0x1a6a110 | 0x1a8a250

The columns in the "show pools" output have the following meanings:

cl_active: Connections from clients which are associated with a PostgreSQL connection
cl_waiting: Connections from clients that are waiting for a PostgreSQL connection to service them
sv_active: Connections to PostgreSQL that are in use by a client connection
sv_idle: Connections to PostgreSQL that are idle, ready to service a new client connection
sv_used: PostgreSQL connections recently released from a client session. These will end up in sv_idle if they need to once pgbouncer has run a check query against them to ensure they are in a good state.
max_wait: The length of time the oldest waiting client has been waiting for a connection

If you want to monitor the connections over a short period of time you can run this command (while logged in as the cchq user): ``watch -n 2 pgb_top``
You can also access the pgbouncer console easily with this command (while logged in as the cchq user): ``pgb``

Postgres Troubleshooting
========================

Common restart problems
-----------------------

If you see something like the following line in the logs:

could not open file ""/etc/ssl/certs/ssl-cert-snakeoil.pem"": Permission denied
You can run the following commands to fix it

.. code-block::

   cd /opt/data/postgresql/9.4/main/
   chown postgres:postgres server.crt
   chown postgres:postgres server.key

More information on this error is available `here <https://wiki.postgresql.org/wiki/May_2015_Fsync_Permissions_Bug>`_.

Dealing with too many open connections
--------------------------------------

Sometimes Postgres gets into a state where it has too many open connections. In this state HQ gets very slow and you will see many 500 errors of the form: "OperationalError : FATAL:  remaining connection slots are reserved for non-replication superuser connections"

In this case you can check what machines are hogging connections by logging into postgres and using the following steps:

Get a postgres shell
^^^^^^^^^^^^^^^^^^^^

.. code-block::

   $ su
   $ sudo -u postgres psql commcarehq

Check open connections
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sql

   select client_addr, datname as database, count(*) as total, sum(case when query = '<IDLE>' then 1 else 0 end) as idle from pg_stat_activity group by client_addr, datname;

This will print something like the following:

.. code-block::

     client_addr   | database   | total | idle
   ----------------+------------+-------+------
                   | commcarehq |    4 |   2
    10.209.128.58  | commcarehq |    9 |   5
    10.177.130.82  | commcarehq |    7 |   7
    10.208.22.37   | commcarehq |    6 |   5
    10.223.145.60  | commcarehq |    1 |   0
    10.208.148.179 | commcarehq |    3 |   3
    10.176.132.63  | commcarehq |   24 |   23
    10.210.67.214  | commcarehq |    3 |   2

When using pgbouncer the following command can be used to list clients:

.. code-block::

   $ psql -h localhost -p 6432 -U $USERNAME pgbouncer -c "show clients" | cut -d'|' -f 5 | tail -n +4 | sort | uniq -c
       10  10.104.103.101
        5  10.104.103.102
        2  10.104.103.104

See Running Queries
^^^^^^^^^^^^^^^^^^^

To see a list of queries (ordered by the long running ones first) you can do something like the following. This can also be exported to csv for further analysis.

.. code-block:: sql

   SELECT pid, datname, query_start, now() - query_start as duration, state, query as current_or_last_query FROM pg_stat_activity WHERE state = 'active' OR query_start > now() - interval '1 min' ORDER BY state, query_start;

 This can also be exported to csv for further analysis.

.. code-block:: sql

   Copy (SELECT state, query_start, client_addr, query FROM pg_stat_activity ORDER BY query_start) TO '/tmp/pg_queries.csv' WITH CSV;

Find queries that are consuming IO
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``iotop`` to see what processes are dominating the IO and get their process IDs.

Filter the list of running queries by process ID:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sql

   SELECT pid, query_start, now() - query_start as duration, client_addr, query FROM pg_stat_activity WHERE procpid = {pid} ORDER BY query_start;

Kill connections
^^^^^^^^^^^^^^^^

*DO NOT EVER ``kill -9`` any PostgreSQL processes. It can bring the DB process down.*

This shouldn't be necessary now that we've switched to using pgbouncer (but it still is currently!).

After checking open connections you can kill connections by IP address or status. The following command will kill all open IDLE connections from localhost (where pgbouncer connections route from) and is a good way to reduce the load:

Kill all idle connections
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   SELECT pg_terminate_backend(procpid) FROM pg_stat_activity WHERE client_addr = '127.0.0.1' AND query = '<IDLE>';

Kill a single query
~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   SELECT pg_terminate_backend({procpid})

Replication Delay
^^^^^^^^^^^^^^^^^

https://www.enterprisedb.com/blog/monitoring-approach-streaming-replication-hot-standby-postgresql-93


* Check if wal receiver and sender process are running respectively on standby and master using ``ps aux | grep receiver`` and ``ps aux | grep sender``
* Alternatively use SQL ``select * from pg_stat_replication`` on either master or standby
* If WAL processes are not running, check logs, address any issues and may need to reload/restart postgres
* Check logs for anything suspicious
* Checking replication delay

  * `Use datadog <https://app.datadoghq.com/dash/263336/postgres---overview?live=true&page=0&is_auto=false&from_ts=1511770050831&to_ts=1511773650831&tile_size=m&tpl_var_env=*&fullscreen=253462140&tpl_var_host=*>`_
  * Run queries on nodes:

.. code-block:: sql

   --- on master
   select
     slot_name,
     client_addr,
     state,
     pg_size_pretty(pg_xlog_location_diff(pg_current_xlog_location(), sent_location)) sending_lag,
     pg_size_pretty(pg_xlog_location_diff(sent_location, flush_location)) receiving_lag,
     pg_size_pretty(pg_xlog_location_diff(flush_location, replay_location)) replaying_lag,
     pg_size_pretty(pg_xlog_location_diff(pg_current_xlog_location(), replay_location)) total_lag
   from pg_replication_slots s
   left join pg_stat_replication r on s.active_pid = r.pid
   where s.restart_lsn is not null;

   -- On standby

   SELECT now() - pg_last_xact_replay_timestamp() AS replication_delay;

In some cases it may be necessary to restart the standby node.

PostgreSQL disk usage
---------------------

Use the following query to find disc usage by table where child tables are added to the usage of the parent.

Table size
^^^^^^^^^^

.. code-block:: sql

   SELECT *, pg_size_pretty(total_bytes) AS total
       , pg_size_pretty(index_bytes) AS INDEX
       , pg_size_pretty(toast_bytes) AS toast
       , pg_size_pretty(table_bytes) AS TABLE
     FROM (
     SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
         SELECT c.oid,nspname AS table_schema, relname AS TABLE_NAME
                 , c.reltuples AS row_estimate
                 , pg_total_relation_size(c.oid) AS total_bytes
                 , pg_indexes_size(c.oid) AS index_bytes
                 , pg_total_relation_size(reltoastrelid) AS toast_bytes
             FROM pg_class c
             LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE relkind = 'r'
     ) a
   ) a order by total_bytes desc;

Table size grouped by parent table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sql

   SELECT
     main_table,
     row_estimate,
     pg_size_pretty(total_size) as total,
     pg_size_pretty(index_bytes) as index,
     pg_size_pretty(toast_bytes) as toast
   FROM (
   SELECT
       CASE WHEN HC.inhrelid IS NOT NULL THEN CP.relname
           ELSE C.relname END as main_table,
       sum(C.reltuples) AS row_estimate, 
       sum(pg_total_relation_size(C.oid)) AS "total_size",
       sum(pg_indexes_size(C.oid)) AS index_bytes,
       sum(pg_total_relation_size(C.reltoastrelid)) AS toast_bytes
   FROM pg_class C
   LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
   LEFT JOIN pg_inherits HC ON (HC.inhrelid = C.oid)
   LEFT JOIN pg_class CP ON (HC.inhparent = CP.oid)
   WHERE nspname NOT IN ('pg_catalog', 'information_schema')
       AND C.relkind <> 'i' AND C.relkind <> 'S' AND C.relkind <> 'v'
       AND nspname !~ '^pg_toast'
   GROUP BY main_table
   ORDER BY total_size DESC
   ) as a;

Table stats grouped by parent table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sql

   SELECT
       CASE WHEN HC.inhrelid IS NOT NULL THEN CP.relname
           ELSE C.relname END as main_table,
       sum(seq_scan) as seq_scan,
       sum(seq_tup_read) as seq_tup_read,
       sum(idx_scan) as idx_scan,
       sum(idx_tup_fetch) as idx_tup_fetch,
       sum(n_tup_ins) as n_tup_ins,
       sum(n_tup_upd) as n_tup_upd,
       sum(n_tup_del) as n_tup_del,
       sum(n_tup_hot_upd) as n_tup_hot_upd,
       sum(n_live_tup) as n_live_tup,
       sum(n_dead_tup) as n_dead_tup    
   FROM pg_class C
   LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
   LEFT JOIN pg_inherits HC ON (HC.inhrelid = C.oid)
   LEFT JOIN pg_class CP ON (HC.inhparent = CP.oid)
   LEFT JOIN pg_stat_user_tables t ON (C.oid = t.relid)
   WHERE nspname NOT IN ('pg_catalog', 'information_schema')
       AND C.relkind <> 'i' AND C.relkind <> 'S' AND C.relkind <> 'v'
       AND nspname !~ '^pg_toast'
   GROUP BY main_table
   ORDER BY n_tup_ins DESC;

Disk Full on Data partition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Case PostgreSQL fails with  ``No space left on device`` error message and in order to free up space needed to restart the PostgreSQL then take the following steps


* Stop the ``Pgbouncer``
* There is a dummy file of 1GB placed in encrypted root path ``/opt/data/emerg_delete.dummy`` which can be deleted.
* It will give you enough space to restart Database. Reclaim the disk space.
* Start the ``Pgbouncer``
* Once the issue has been resolved you should re-add the dummy file for future use:
  .. code-block::

      dd if=/dev/zero of=/opt/data/emerg_delete.dummy count=1024 bs=1048576

Deleting old WAL logs
^^^^^^^^^^^^^^^^^^^^^

At all the times, PostgreSQL maintains a write-ahead log (WAL) in the pg_xlog/ for version <10 and in pg_wal/ for version >=10 subdirectory of the cluster’s data directory. The log records for every change made to the database’s data files. These log messages exists primarily for crash-safety purposes.

It contains the main binary transaction log data or binary log files. If you are planning for replication or Point in time Recovery, we can use this transaction log files.

We cannot delete this file. Otherwise, it causes a database corruption. The size of this folder would be greater than actual data so If you are dealing with massive database, 99% chance to face disk space related issues especially for the pg_xlog or pg_wal folder.

There could be multiple reason for folder getting filled up.


* Archive Command is failing.
* Replication delay is high.
* Configuration params on how much WAL logs to keep.

If you are able to fix the above related , then logs from this folder will be cleared on next checkpoints.

If it's absolutely necessary to delete the logs from this folder. Use following commands to do it. (Do not delete logs from this folder manually)

.. code-block::

   # you can run this to get the latest WAL log
   /usr/lib/postgresql/<postgres-version>/bin/pg_controldata /opt/data/postgresql/<postgres-version>/main

   Deleting 
   /usr/lib/postgresql/<postgres-version>/bin/pg_archivecleanup -d /opt/data/postgresql/<postgres-version>/main/<pg_wal|| pg_xlog> <latest WAL log filename>

Celery
======

Check out :ref:`reference/firefighting/celery:Celery Firefighting Guide`.

Monitoring
----------

Sometimes it's helpful to check "Flower", a UI for celery monitoring http://hqcelery1.internal-va.commcarehq.org:5555/ (you have to be VPN'd in).

You can also check the current celery queue backlogs on datadog.  Any spikes indicate a backup, which may result in things like delays in sending scheduled reports or exports.  If there's a problem, there should also be an alert here and on #hq-ops on Slack.

Also, see the bottom of this page for some useful firefighting commands.

Celery consuming all the disk space
-----------------------------------

On occasion, the celery_taskmeta table grows out of control and takes up all the disk space on the database machine very quickly. Often one our disk space monitors will trip when this happens. To diagnose and ensure that the it is indeed the celery_taskmeta table that has grown too large, you can run the above Postgres command to check disk usage by table.

To fix the issue, you can then run these commands in a psql shell after stopping the Celery workers:

.. code-block::

   # Ensure Celery workers have been stopped
   truncate celery_taskmeta;
   vacuum full celery_taskmeta;
   # Start Celery workers again

Elasticsearch
=============

Check Cluster Health
--------------------

It's possible to just ping (a) server(s):

.. code-block::

   $ curl -XGET 'http://es[0-3].internal-icds.commcarehq.org:9200/'
   {
     "status" : 200,
     "name" : "es0",
     "cluster_name" : "prodhqes-1.x",
     "version" : {
       "number" : "1.7.3",
       "build_hash" : "05d4530971ef0ea46d0f4fa6ee64dbc8df659682",
       "build_timestamp" : "2015-10-15T09:14:17Z",
       "build_snapshot" : false,
       "lucene_version" : "4.10.4"
     },
     "tagline" : "You Know, for Search"
   }

Or check for health:

.. code-block::

   $ curl -XGET 'http://es0.internal-icds.commcarehq.org:9200/_cluster/health?pretty=true'
   {
     "cluster_name" : "prodhqes-1.x",
     "status" : "green",
     "timed_out" : false,
     "number_of_nodes" : 4,
     "number_of_data_nodes" : 4,
     "active_primary_shards" : 515,
     "active_shards" : 515,
     "relocating_shards" : 0,
     "initializing_shards" : 0,
     "unassigned_shards" : 0,
     "delayed_unassigned_shards" : 0,
     "number_of_pending_tasks" : 0,
     "number_of_in_flight_fetch" : 0
   }

Data missing on ES but exist in the primary DB (CouchDB / PostgreSQL)
---------------------------------------------------------------------

We've had issues in the past where domains have had some of their data missing from ES.
This might correlate with a recent change to ES indices, ES-related upgrade work, or ES performance issues.
All of these instabilities can cause strange flaky behavior in indexing data, especially in large projects.

First, you need to identify that this issue is not ongoing and widespread. 

1) visit the affected domain's Submit History or Case List report to verify that recent submissions are still being indexed on ES
(if they are in the report, they are in ES)
2) check the modification date of the affected data and then check the reports around that date and surrounding dates.
3) spot check another domain with a lot of consistent submissions to see if there are any recent and past issues
surrounding the reported affected date(s).

If you don't see any obvious issues, it's likely a strange data-flakiness issue. This can be resolved by running the
following management commands (run in a tmux since they may take a long time to complete):

.. code-block:: bash

   pthon manage.py stale_data_in_es [form/case] --domain <domain> [--start=YYYY-MM-DD] [--end=YYYY-MM-DD] > stale_data.tsv
   pthon manage.py republish_doc_changes stale_data.tsv

You can also do a quick analysis of the output data to find potentially problematic dates:

.. code-block:: bash

   cat state_data.tsv | cut -f 6 | tail -n +2 | cut -d' ' -f 1 | uniq -c

         2 2020-10-26
       172 2020-11-03
        14 2020-11-04

If you DO see obvious issues, it's time to start digging for problematic PRs or checking performance monitoring graphs.

Low disk space free
-------------------

"[INFO ][cluster.routing.allocation.decider] [hqes0] low disk watermark [85%] exceeded on ... replicas will not be assigned to this node"

is in the logs, then ES is running out of disk space.  If there are old, unused indices, you can delete them to free up disk space.

.. code-block::

   $ ./manage.py prune_elastic_indices --delete
   Here are the indices that will be deleted:
   hqapps_2016-07-08_1445
   hqusers_2016-02-16_1402
   report_xforms_20160707_2322
   xforms_2016-06-09

Hopefully there are stale indices to delete, otherwise you'll need to investigate other options, like increasing disk size or adding a node to the cluster.  Be sure to check the disk usage after the deletions have completed.

Request timeouts
----------------

"ESError: ConnectionTimeout caused by - ReadTimeoutError(HTTPConnectionPool(host='hqes0.internal-va.commcarehq.org', port=9200): Read timed out. (read timeout=10))"

This could be caused by a number of things but a good process to follow is to check the `ES dashboard on Datadog <https://app.datadoghq.com/screen/127236/es-overview>`_ and the slow logs on the ES machines:

.. code-block::

   # folder + filename may not be exact
   $ tail -f /opt/data/elasticsearch-1.7.1/logs/prodhqes-1.x_index_search_slowlog.log

Unassigned shards
-----------------

Currently on ICDS (maybe on prod/india) shard allocation is disabled. In case a node goes down all the shards that were on the node get unassigned. Do not turn on automatic shard allocation immediately since that might cause lot of unexpected shards to move around. Instead follow below instructions (the last point is very important for large ES clusters)


* Check which nodes are down and restart them.
* Once all nodes are up, all the primary nodes should automatically get assigned.

  * Shard assignment can be checked via Elasticsearch `shards API <https://www.elastic.co/guide/en/elasticsearch/reference/current/cat-shards.html>`_ or the shards graph on Elasticsearch datadog dashboard

* 
  If any primaries are not allocated. Use rereoute API (\ `official docs <https://www.elastic.co/guide/en/elasticsearch/reference/2.4/cluster-reroute.html>`_\ )


  * Reroute according to existing shard allocation
  * 
    The rerouting of unassigned primary shards will cause data loss (w.r.t es_2.4.6). :raw-html-m2r:`<br>`
    :warning: The :raw-html-m2r:`<b>allow_primary</b>` parameter will force a new empty primary shard to be allocated without any data. If a node which has a copy of the original shard (including data) rejoins the cluster later on, that data will be deleted: the old shard copy will be replaced by the new live shard copy.

  * 
    Example reroute command to allocate replica shard

    .. code-block::

       curl -XPOST 'http://<es_url>/_cluster/reroute' -d ' {"commands" :[{"allocate": {"shard": 0, "node": "es34", "index": "xforms_2020-02-20"}}]}'

* 
  Replicas won’t get auto assigned. To assign replicas, auto shard allocation needs to be enabled


  * Make sure no primaries are unassigned
  * Turn on auto shard allocation using
    .. code-block::

       curl 'http://<es_url>/_cluster/settings/' -X PUT  --data '{"transient":{"cluster.routing.allocation.enable":"all"}}'

  * Wait for replicas to get assigned.

* Finally **remember to turn off** auto shard allocation using
  .. code-block::

       curl 'http://<es_url>/_cluster/settings/' -X PUT  --data '{"transient":{"cluster.routing.allocation.enable":"none"}}'

.. code-block::

   curl -XPUT '<es url/ip>:9200/_cluster/settings' -d '{ "transient":
     { "cluster.routing.allocation.enable" : "all"
     }
   }'
   # wait for shards to be allocated
   ./scripts/elasticsearch-administer.py <es url> shard_status # all shards should say STARTED
   curl -XPUT '<es url/ip>:9200/_cluster/settings' -d '{ "transient":
     { "cluster.routing.allocation.enable" : "none"
     }
   }'
   ./manage.py ptop_reindexer_v2 <index that had the unassigned shards> # run this in a tmux/screen session as it will likely take a while
   ./scripts/elasticsearch-administer.py <es url> shard_status # the shards for indexes that had unassigned shards should have around the same number of docs

Make sure to run the management command in the most recent release directory (may not be current if this failed before the entire deploy went through)

Redis
=====

`Understanding the Top 5 Redis Performance Metrics <https://www.datadoghq.com/pdf/Understanding-the-Top-5-Redis-Performance-Metrics.pdf>`_

Selectively flushing keys
-------------------------

Sometimes in order for a fix to propagate you'll need to flush the cache for certain keys. You can use this script to selectively flush keys by globbing.

.. code-block::

   redis-cli
   127.0.0.1:6379> EVAL "local keys = redis.call('keys', ARGV[1]) \n for i=1,#keys,5000 do \n redis.call('del', unpack(keys, i, math.min(i+4999, #keys))) \n end \n return keys" 0 unique-cache-key*

A lot of times Redis will prefix the cache key with something like ``:1:`` so you'll often need to do *unique-cache-key*

Disk full / filling rapidly
---------------------------

Is maxmemory set too high wrt actual memory?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We have seen a situation where the redis disk fills up with files of the pattern /opt/data/redis/temp-rewriteaof-*.aof. This happens when redis maxmemory is configured to be too high a proportion of the total memory (although the connection is unclear to the author, Danny). This blog http://oldblog.antirez.com/post/redis-persistence-demystified.html/ explains AOF rewrite files. The solution is to (1) lower maxmemory and (2) delete the temp files.

.. code-block::

   root@redis0:/opt/data/redis# cd /opt/data/redis/
   root@redis0:/opt/data/redis# redis-cli
   127.0.0.1:6379> CONFIG SET maxmemory 4gb
   OK
   (1.06s)
   root@redis0:/opt/data/redis# rm temp-rewriteaof-\*.aof

Is your disk at least 3x your maxmemory?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We use the `default AOF auto-rewrite configuration <https://github.com/redis/redis/blob/5.0/redis.conf#L757-L770>`_\ , which is to rewrite the AOF (on-disk replica of in-memory redis data) whenever it doubles in size. Thus disk usage will sawtooth between X and 3X where X is the size of the AOL after rewrite: X right rewrite, 2X when rewrite is triggered, and 3X when the 2X-sized file has been written to a 1X-sized file, but the 2X-sized file has not yet been deleted, followed finally again by X after rewrite is finalized and the old file is deleted.

Since the post-rewrite AOF will only ever contain as much data as is contained in redis memory, and the amount of data contained in redis memory has an upper bound of the maxmemory setting, you should make sure that your disk is at least 3 * maxmemory + whatever the size of the OS install is. Since disk is fairly cheap, give it a comfortable overhead for log files etc.

Checking redis after restart
----------------------------

Redis takes some time to read the AOF back into memory upon restart/startup. To check if it's up, you can run the following:

.. code-block:: memory

   $ cchq <env> ssh ansible@redis

   % redis-cli
   127.0.0.1:6379> ping
   (error) LOADING Redis is loading the dataset in memory
   127.0.0.1:6379> ping
   (error) LOADING Redis is loading the dataset in memory
   127.0.0.1:6379> ping
   PONG

once it responds with ``PONG`` redis is back up and ready to serve requests.

Tail the redis log
------------------

To show the last few lines of the redis log during firefighting you can run:

.. code-block::

   cchq <env> run-shell-command redis 'tail /opt/data/redis/redis.log'

Pillows / Pillowtop / Change feed
=================================

Symptoms of pillows being down:


* Data not appearing in reports, exports, or elasticsearch
* UCR or report builder reports behind
* `Datadog monitor <https://app.datadoghq.com/monitors#4013126?group=all&live=1d>`_

Resources:


* `graph of change feed activity <https://app.datadoghq.com/dash/256236/change-feeds?live=true&page=0&is_auto=false&from_ts=1518372763225&to_ts=1518459163225&tile_size=m&fullscreen=185100827>`_
* `Pillows documentation <https://commcare-hq.readthedocs.io/pillows.html>`_
* `Pillows overview and introduction <https://docs.google.com/presentation/d/1xgEZBer-FMUkeWutrTRcRbqKzVToK6mZvl0x2628BGY/edit#slide=id.p>`_

Managing Pillows
----------------

You can check on the status of the pillow processors with

.. code-block::

   cchq <env> service pillowtop status

and you can restart a pillow which is not currently ``RUNNING`` with

.. code-block::

   cchq <env> service pillowtop start --only=<pillow_name>

Note that the elements returned by the ``status`` command are the names of the processors, not the names of the pillows themselves. 

For example if the status command identified that ``myenv-production-DefaultChangeFeedPillow-0`` was not running, to restart the pillow one would run 

.. code-block::

   #Correct - Restarting by pillow name
   cchq myenv service pillowtop start --only=DefaultChangeFeedPillow

rather than

.. code-block::

   #Incorrect - Restarting by processor name
   cchq myenv service pillowtop start --only=myenv-production-DefaultChangeFeedPillow-0

Formplayer / Cloudcare / Webapps
================================

Formplayer sometimes fails on deploy due to a startup task (which will hopefully be resolved soon).  The process may not fail, but formplayer will still return failure responses. You can try just restarting the process with ``sudo supervisorctl restart all`` (or specify the name if it's a monolithic environment)

A formplayer machine(s) may need to be restarted for a number of reasons in which case you can run (separate names by comma to run on multiple machines):

.. code-block::

   cchq <env> service formplayer restart --limit=formplayer_bXXX

Lock issues
-----------

If there are many persistent lock timeouts that aren't going away by themselves,
it can be a sign of a socket connection hanging and Java not having a timeout
for the connection and just hanging.

In that case, it can be helpful to kill the offending socket connections. The following command queries for socket connections
that look like the ones that would be hanging and kills them:

.. code-block::

   cchq <env> run-shell-command formplayer 'ss src {{ inventory_hostname }} | grep ESTAB | grep tcp | grep ffff | grep https | cut -d: -f5 | cut -d -f1 | xargs -n1 ss -K sport = ' -b

Because it's filtered, it won't kill *all* socket connections, but it will kill more socket connections than strictly necessary,
since it is difficult to determine which specific connections are the problematic ones. But anecdotally this
doesn't cause any user-facing problems. (I still wouldn't do it unless you have to to solve this issue though!)

Full Drives / Out of Disk Space
===============================

If disk usage on the proxy ever hits 100%, many basic functions on the machine will stop working.  Here are some ways to buy some time.

Basic Commands
--------------

You can probe statistics before taking any action. `df -h` or `dh -h /` will show total disk usage. To query specific directory/file usage, use:
`du -hs <path>`. Note that these commands still respect permissions. If you need elevated permissions, you can ssh to the affected machine as the ansible user
(cchq --control <env> ssh ansible@<machine>), and from there you can use sudo. The ansible password can be found within 1Pass

Clean Releases
--------------

Each release / copy of our commcare-hq git repo can be 500M - 2.7G (variation can depend on how efficiently git is storing the history, etc.). It's always safe to run

``$ cchq <env> fab clean_releases``
and sometimes that alone can clean up space. This is run on every deploy, so if you just deployed successfully, don't bother.

Move logs to another drive
--------------------------

Check the size of the log files stored at /home/cchq/www/\ :raw-html-m2r:`<environment>`\ /log, these can get out of hand.  Last time this ocurred, we moved these into the shared drive, which had plenty of available disk space (but check first!)

``$ mv -v pattern-matching-old-logs.*.gz /mnt/shared/temp-log-storage-main-hd-full/``

Clear the apt cache
-------------------

Apt stores its files in */var/cache/apt/archives*. Use `du` as describe above to determine if this cache is consuming too much space.
If it is, these files can be cleaned via `apt-get clean``

``$ apt-get autoremove``
This removes packages that are no longer required. Sometimes the savings can be substantial. If you run the above command, it should show you how much space it expects to free up, before you commit to running it.
On a recent occasion, this freed up about 20% of the disk

Manually rotate syslog
----------------------

If for some reason syslog is either not rotating logs or the latest log has grown more than expected you can run

.. code-block::

   mv syslog other.syslog
   kill -HUP <pid of syslog>
   gzip other.syslog

Look at temp folders
--------------------

On celery machines, specifically, tasks can generate a large volume of temporary files. Use `du` against */opt/tmp* and compare these results
to other machines to determine if this is the likely issue. If so, some of these files may still be in use. These files will likely be cleared
once the task has completed. If not, we have an automated task that cleans up files older than 2 days. If disk space is in a dire situation,
it may be possible to remove some of the older files (using `lsof <file>` or `lsof +D <directory>` can help find what files are in use)

Network Connection Issues (please help expand)
==============================================

If you suspect some sort of network issue is preventing two servers from talking to each other, the first thing you should verify is that the processes you expect to talk to each other are actually running.  After that, here are some things to try:

Ping
----

Try pinging the machine from the computer you'd expect to initiate the connection.  If that doesn't work, try pinging from your local machine while on the VPN.

.. code-block::

   esoergel@hqproxy0:~$ ping hqdb0.internal-va.commcarehq.org
   PING hqdb0.internal-va.commcarehq.org (172.24.32.11) 56(84) bytes of data.
   64 bytes from 172.24.32.11 (172.24.32.11): icmp_seq=1 ttl=64 time=42.6 ms
   64 bytes from 172.24.32.11 (172.24.32.11): icmp_seq=2 ttl=64 time=41.3 ms

netcat
------

Netcat is a mini server.  You can set it up to listen on any port and respond to requests.  Run something like this to listen on port 1234 and wait for a request:

``esoergel@hqdb0:~$ printf "Can you see this?" | netcat -l 1234``

Then go over to the other machine and try to hit that server:

.. code-block::

   $ curl hqdb0.internal-va.commcarehq.org:1234
   Can you see this?$

Looks like the request went through!  If you go back and check on the netcat process, you should see the request:

.. code-block::

   esoergel@hqdb0:~$ printf "Can you see this?" | netcat -l 1234
   HEAD / HTTP/1.1
   Host: hqdb0.internal-va.commcarehq.org:1234
   User-Agent: curl/7.50.1
   Accept: */*

   esoergel@hqdb0:~$

Tips and Tricks
===============

Never run that painful sequence of sudo -u cchq bash, entering the venv, cd'ing to the directory, etc., again just to run a management command. Instead, just run e.g.:

.. code-block::

   cchq <env> django-manage shell --tmux

first thing after logging in.

Some Short Write-ups and Examples
=================================

See `Troubleshooting Pasteboard / HQ chat dumping ground <https://confluence.dimagi.com/pages/viewpage.action?pageId=29559520>`_. There is also some `ElasticSearch material <https://docs.google.com/a/dimagi.com/document/d/1EMy-m-Q3aia43q_TqeJdAFVLEx6UfEu3vRqSXskpQ_Y/edit#heading=h.xygb2bpkcfie>`_

Backups
=======

Information for restoring elasticsearch and postgres from a backup are at `Restoring From Backups <https://confluence.dimagi.com/display/commcarehq/Restoring+From+Backups>`_

SMS Gateways
============

See the page on `SMS Gateway Technical Info <https://confluence.dimagi.com/display/commcarehq/SMS+Gateway+Technical+Info>`_ for API docs and support contacts for each gateway.
