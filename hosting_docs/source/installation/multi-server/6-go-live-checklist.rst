Go-Live Checklist
=================

Personnel 
---------

The local organization identifies a Managed Service Provider (MSP) that
will administer the CommCare HQ software suite. Managing a deployment of
CommCare requires a team of two to five full-time DevOps engineers,
depending on the size of the deployment. Hardware provisioning, regular
software deployments, system performance monitoring and security audits
are included within the scope of the MSP. All engineers should be
onboarded and be familiar with the
`CommCare Cloud deployment documentation`_ prior to starting the system
installation. 


Mobile Application Release
--------------------------

During the migration process users must stop syncing data to the
development environment and change over to the production environment.
To facilitate the process with minimal user interruption, changing the
application to synchronize to a custom URL enables the MSP to toggle
requests to the development environment, then after the migration, to
the new server. This change occurs at the DNS level without requiring a
change on each device. 

The MSP sets up a domain name to be used for the migration, enables the
application toggle, and releases a new build. This application change
should be pushed to all users prior to initiating any data migration
steps. Users who do not update their applications will be locked out
once the switch to the local server takes place. Detailed documentation
for implementing this mobile application change are available online and
should be completed prior to the local system installation. 

The MSP is required to provide a domain name that they own and control,
and will be required to add a special, temporary DNS entry in order for
Dimagi's SSL certificate to work properly.

Documentation:

* `Switch mobile devices to a proxy URL`_

.. note::
   **Checkpoint: All hardware resources and personnel are available. The
   project team has completed the
   :ref:`hosting-prereqs-pre-deployment-checklist` and shared the
   results with Dimagi. A new version of the mobile application(s) have
   been deployed and released to all users.**


CommCare Installation
---------------------

The MSP is tasked to install the CommCare HQ software suite.

After completing the installation, the MSP runs
:ref:`all applicable tests <hosting-new-environment-qa>` to ensure the
CommCare environment is working as expected. 

.. note::
   **Checkpoint:  Applicable tests are passed. The system performs in
   real conditions.**


Configure Monitoring and Error Logging
--------------------------------------

Real-time monitoring of system activities is essential to understand how
the system is performing at a given moment, and to troubleshoot issues
as they arise. Monitoring helps to forecast resource requirements for
future scaling, and alerts may be set up on various monitoring metrics
to detect resource limits, anomalies which may cause server issues, or
detect security incidents. 

The MSP is tasked with installing and configuring monitoring tools for
CommCare’s hosts and for CommCare’s application / service indicators.
The same tool may be used for both activities, or different tools may be
selected.

Documentation:

* :ref:`Monitoring and Alerting Infrastructure Metrics <hosting-operations-monitoring-alerting>`
* :ref:`Setting up Sentry for error logging <hosting-operations-set-up-sentry>`

.. note::
   **Checkpoint: Pre-set dashboards are imported if using DataDog, or
   system health dashboards have been created if using an alternative
   tool. Sentry has been set up for error logging.**


Test System Backup and Restore Process
--------------------------------------

Dimagi recommends an offsite, ideally cloud-based, backup that is run
automatically. Performing periodic system backups provides a means to
restore the integrity of the system in the event of a hardware or
software failure. Performing a full system backup and restore is a
critical capability of the MSP and as such should be performed prior to
it being relevant.

Documentation:

* :ref:`hosting-backup-guide`

.. note::
   **Checkpoint: A full backup and restore is completed for the entire
   system.**


Data Migration
--------------

A data migration needs to occur if it is expected that mobile workers
will continue working without re-installing their applications, and if
existing data is desired on the locally hosted system. In general the
process for data migration requires strong collaboration between both
Dimagi and the MSP, as the timing of the steps is important, and can
only happen once a local system is up and running.

The MSP is required to provide a secure place for Dimagi to dump data to
(e.g. a secured server which can be accessed by SSH), with enough disk
space for a full data dump, and enough bandwidth to allow a timely
transfer from our servers

Importing a data dump is the MSP's responsibility.

Documentation:

* `Transfer a project to a standalone environment`_

There will be a period of time between when the data dump is being
created and when the data dump is imported to the new server when mobile
workers will not be able to access the system (e.g. syncing, form
submissions), so this expectation should be set with all stakeholders,
including mobile workers. It is also recommended that a dry-run of the
process is carried out to prevent any data loss and to iron out hardware
or configuration issues prior to stopping the production server.

A new, valid SSL certificate for the domain name will need to be
provided and configured at this point.

.. note::
   **Checkpoint: Data is migrated to the local server. Phones sync to
   the local server.**


.. _CommCare Cloud deployment documentation: https://commcare-cloud.readthedocs.io/en/latest/index.html
.. _Switch mobile devices to a proxy URL: https://github.com/dimagi/commcare-cloud/blob/master/docs/howto/transfer-domain.md
.. _Transfer a project to a standalone environment: https://github.com/dimagi/commcare-cloud/blob/master/docs/howto/transfer-domain.md
