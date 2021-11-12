
Managing The Deployment
=======================

.. contents:: Table of Contents
    :depth: 2
    :local:
    :backlinks: none

------------------------
Server Management Basics
------------------------

Manage services
---------------

To manage services you can use the ``service`` command

.. code-block::

   $ commcare-cloud <env> service postgresql [status|start|stop|restart]
   $ commcare-cloud <env> service --help

Stop all CommCare HQ services
-----------------------------

.. code-block::

   $ commcare-cloud <env> service commcare stop
   $ commcare-cloud <env> service commcare start

OR

.. code-block::

   $ commcare-cloud <env> downtime start
   $ commcare-cloud <env> downtime end

In addition to stopping all services this command will
check to see if any processes are still running and give you the
option of terminating them or waiting for them to stop.

Handling a reboot
-----------------

When a server reboots there are a number of tasks that should be run
to ensure that the encrypted drive is decrypted and all systems are
brought back up.

.. code-block::

   $ commcare-cloud <env> after-reboot --limit <inventory name or IP> all

Update CommCare HQ local settings
---------------------------------

To roll out changes to the ``localsettings.py`` file for Django
or the ``application.properties`` file for Formplayer:

.. code-block::

   $ commcare-cloud <env> update-config

Note that you will need to restart the services in order for the changes
to be picked up by the processes.

Run Django Management Commands
------------------------------

To run Django management commands we need to log into a machine which has Django configured. Usually we run these commands on the ``django_manage`` machine which is a ``webworker`` machine.

.. code-block::

   $ cchq <env> ssh django_manage
   $ sudo -iu cchq   #Switch to cchq user
   $ cd /home/cchq/www/<env>/current # Change directory to current django release folder
   $ source python_env/bin/activate  # Activate the python virtual env
   $ ./manage.py <command>  # Run the command

There is also an alternate method for running management commands which can be useful in certain situations:

.. code-block::

   $ cchq <env> django-manage <command> <options>

Here are some common examples:

.. code-block::

   # get a Django shell
   $ cchq <env> django-manage shell

   # get a DB shell
   $ cchq <env> django-manage dbshell --database <dbalias>

   # check services
   $ cchq <env> django-manage check-services

A note about system users
-------------------------

``commcare-cloud`` creates and uses the ``ansible`` user on machines that it manages. You should not login as this user or use it for other things other than automated tasks run by the ansible process. This is especially applicable when you have a ``control`` machine that runs other commcare processes. 

----------------------------------
Deploying CommCare HQ code changes
----------------------------------

This document will walk you through the process of updating the CommCare HQ code on your server using ``commcare-cloud``.

Prerequisites
-------------

Ensure that you have a working version of ``commcare-cloud`` which is configured to act on your monolith or fleet of servers. You can find more information on setting up ``commcare-cloud`` in the `installing ``commcare-cloud`` <../setup/installation.md>`_ documentation. 

If you don't yet have a server with CommCare HQ, you can try `setting up a monolith <../setup/new_environment.md>`_.

All commands listed here will be run from your control machine which has ``commcare-cloud`` installed.

Step 1: Update ``commcare-cloud``
-------------------------------------

We first want to pull the latest code for ``commcare-cloud`` to make sure it has the latest bugfixes by running:

.. code-block:: bash

   $ update-code

This command will update the ``commcare-cloud`` command from GitHub and apply any updates required. You can see exactly what this command does in `this file <https://github.com/dimagi/commcare-cloud/blob/master/control/update_code.sh>`_.

Step 2: Deploy new CommCare HQ code to all machines
---------------------------------------------------

CommCare HQ is deployed using `fabric <http://www.fabfile.org/>`_ , which ensures only the necessary code is deployed to each machine.

Envoke the ``deploy`` command by running:

.. code-block:: bash

   $ commcare-cloud <env> deploy

where you will substitute ``<env>`` for the name of the environment you wish to deploy to.

Preindex Command
^^^^^^^^^^^^^^^^

The first step in deploy is what we call a ``preindex``\ , which updates any CouchDB views and Elasticsearch indices. This only runs when changes need to be made, and may take a while depending on the volume of data that you have in these data stores. You may need to wait for this process to complete in order to complete deploy. 

If your server has email capabilities, you can look out for an email notification with the subject: ``[<env>_preindex] HQAdmin preindex_everything may or may not be complete``. This will be sent to the ``SERVER_EMAIL`` email address defined in the Django settings file.

You can also try running:

.. code-block:: bash

   $ commcare-cloud <env> django-manage preindex_everything --check

If this command exits with no output, there is still a preindex ongoing. 

Step 3: Checking services once deploy is complete
-------------------------------------------------

Once deploy has completed successfully, the script will automatically restart each service, as required. You can check that the system is in a good state by running:

.. code-block:: bash

   $ commcare-cloud <env> django-manage check_services

This will provide a list of all services which are running in an unexpected state.

You may also wish to monitor the following pages, which provide similar information if you are logged in to CommCare HQ as a superuser:


* ``https://<commcare url>/hq/admin/system/``
* ``https://<commcare url>/hq/admin/system/check_services``

--------
Advanced
--------

The following commands may be useful in certain circumstances.

Run a pre-index
---------------

When there are changes that require a reindex of some database indexes it is possible to do that indexing prior to the deploy so that the deploy goes more smoothly.

Examples of change that woud result in a reindex are changes to a CouchDB view, or changes to an Elasticsearch index.

To perform a pre-index:

.. code-block:: bash

   $ commcare-cloud <env> fab preindex_views

Resume failed deploy
--------------------

If something goes wrong and the deploy fails part way through you may be able to resume it as follows:

.. code-block:: bash

   $ commcare-cloud <env> deploy --resume

Roll back a failed deploy
-------------------------

You may also wish to revert to a previous version of the CommCare HQ code if the version you just deployed was not working for some reason. Before reverting, you should ensure that there were no database migrations that were run during the previous deploy that would break if you revert to a previous version.

.. code-block:: bash

   $ commcare-cloud <env> fab rollback

Deploy static settings files
----------------------------

When changes are made to the static configuration files (like ``localsettings.py``\ ), you will need to deploy those static changes independently. 

.. code-block:: bash

   $ cchq <env> update-config

Deploying Formplayer
--------------------

In addition to the regular deploy, you must also separately deploy the service that backs Web Apps and App Preview, called formplayer. Since it is updated less frequently, we recommend deploying formplayer changes less frequently as well. Doing so causes about 1 minute of service interruption to Web Apps and App Preview, but keeps these services up to date.

.. code-block:: bash

   commcare-cloud <env> deploy formplayer

Formplayer static settings
--------------------------

Some Formplayer updates will require deploying the application settings files. You can limit the local settings deploy to only Formplayer machines to roll these out

.. code-block:: bash

   $ cchq <env> update-config --limit formplayer

------------------
Scheduling Deploys
------------------

CommCare deploy
---------------

Internally at Dimagi the main cloud environment is deployed **every weekday**. 

However, for locally hosted deployments, we recommend deploying **once a week** (for example, every Wednesday), to keep up to date with new features and security patches.

Since CommCare HQ is an Open Source project, you can see all the new features that were recently merged by looking at the `merged pull requests <https://github.com/dimagi/commcare-hq/pulls?q=is%3Apr+is%3Aclosed>`_ on GitHub.

Formplayer deploy
-----------------

In addition to the regular deploy, we recommend deploying formplayer **once a month**.

Local Settings deploy
---------------------

Settings generally only need to be deployed when static files are updated against your specific environment. 

Sometimes changes are made to the system which require new settings to be deployed before code can be rolled out. In these cases, the detailed steps are provided in the `changelog <../changelog/index.md>`_. Announcements are made to the `Developer Forum <https://forum.dimagi.com/>`_ in a `dedicated category <https://forum.dimagi.com/c/developers/maintainer-announcements/>`_ when these actions are needed. We strongly recommend that anyone maintaining a CommCare Cloud instance subscribe to that feed.

-------------------------------
Resolving problems with deploys
-------------------------------

This document outlines how to recover from issues which are enountered when performing deploys from ``commcare-cloud``.

Make sure you are up to date with the documented process for `deploying to servers <deploy.md>`_. 

All commands listed here will be run from your control machine which has ``commcare-cloud`` installed.

Local Settings Mismatch
-----------------------

If local settings files don't match the state expected by ansible during the deploy will fail.

Potential Causes
^^^^^^^^^^^^^^^^

If ``commcare-cloud`` is not up to date when a deploy is run, the resulting deploy may change the local configuration of services in unintended ways, like reverting localsettings files pushed from an up-to-date deploy. If ``commcare-cloud`` is then updated and a new deploy occurs, the deploy can fail due to the ambiguous state.

Example Error
^^^^^^^^^^^^^

Here is an example of this error which could result from


* User A updates ``commcare-cloud`` to add ``newfile.properties`` to ``formplayer`` and deploys that change
* User B deploys ``formplayer`` with an out-of-date ``commcare-cloud`` instance which doesn't include User A's changes
* User B updates ``commcare-cloud`` and attempts to deploy again

.. code-block:: bash

   TASK [formplayer : Copy formplayer config files from current release] ***********************************************************************************************************************************************************************
   failed: [10.200.9.53] (item={u'filename': u'newfile.properties'}) => {"ansible_loop_var": "item", "changed": false, "item": {"filename": "newfile.properties"}, "msg": "Source /home/cchq/www/production/formplayer_build/current/newfile.properties not found"}

Resolution
^^^^^^^^^^

After updating ``commcare-cloud`` and ensuring everything is up to date, running a `static settings deploy <deploy.md#deploy-static-settings-files>`_ on the relevant machines should fix this problem, and allow the next deploy to proceed as normal.
