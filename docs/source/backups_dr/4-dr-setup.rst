Disaster Recovery
=================


.. contents:: Table of Contents
    :depth: 2

Overview
--------

Disaster Recovery refers to the process of restoring the IT services following an event of outage of IT infrastructure due to a natural or human induced disaster to allow business continuity. This `public article <https://www.ibm.com/in-en/topics/backup-disaster-recovery>`_ from IBM is useful to understand what Disaster Recovery is in general.

A Disaster Recovery solution at a minimum involves

*
  Establishing Recovery Time and Recovery Point Objectives that meet project requirements.

*
  Setting up and monitoring remote data backups or replication.

*
  Creating an active or passive secondary site and the necessary automation to failover and restore to this site rapidly.

Since CommCare Mobile works offline, a disaster at primary infrastructure may not cause an immediate disruption to mobile worker operations. But it definitely impacts all web operations (for e.g. actions based on reports, SMS reminders and integrations) and will soon clog mobile worker operations as well. 

In this regard, to ensure continuity of a CommCare deployment following an event of outage, you must have a comprehensive Disaster Recovery Solution. The purpose of this document is not to present any single Disaster Recovery solution, but rather to present the possibilities and components that commcare-cloud provides to enable a Disaster Recovery. The specific solution may vary depending on business needs, IT capacity and DR budget and we recommend you to design a DR solution that meets all of your requirements upfront as part of initial CommCare deployment. 


Setting up a secondary environment
----------------------------------

To set up a secondary environment, copy the existing environment :ref:`config directory <configure-env>` to another directory and use it to :ref:`install CommCare HQ <deploy-commcarehq>`.

If you plan to have a secondary environment identical to primary environment the only file you will need to update is the inventory file with IP addresses from secondary environment.

If not, you can create another environment directory with updated configuration based on the primary config directory.


Remote Backups
--------------

The commcare-cloud backup tool provides everything to enable remote backups. It takes daily and weekly backups by default and can be configured to take hourly backups. The tool can send backups to a remote S3 compatible service if configured. The documenation on :ref:`backups` has the relevant details on how to set up remote backups and restore from backups.

While the remote backups are the minimum requirement to safeguard the data in the event of a disaster it is not enough for a rapid recovery of the CommCare services. Even though, commcare-cloud is able to provide hourly backups it will not be enough to achieve one hour RPO since it is not possible to set up a CommCare environment rapidly in an hour at a secondary site. To enable rapid recovery you must have a secondary environment on standby, set up database replication and a failproof recovery plan and scripts.

Database Replication
--------------------

Continous Database replication is necessary to enable minimal RPO. While commcare-cloud does not have tooling available to set up continous replication all the databases used in CommCareHQ support replication through various means. To set this up, you should consult database specific documentation and set this up yourself.

Primary Databases

*
  Postgresql https://www.postgresql.org/docs/current/runtime-config-replication.html

*
  BlobDB If you are using MinIO https://min.io/product/active-data-replication-for-object-storage

*
  CouchDB https://docs.couchdb.org/en/stable/replication/intro.html

Secondary Databases

* Elasticsearch https://www.elastic.co/guide/en/cloud-enterprise/2.4/ece-snapshots.html#ece-restore-across-clusters


Example models
--------------

Below are some example models for DR.

*
  Remote backups on secondary environment: You can set up a CommCare HQ environment on secondary infrastructure, keep it up to date with remote backups and keep restore scripts ready.

*
  Secondary environment with contious data replication: You can setup a fully functioning secondary environment with databases being replicated continously.

*
  Remote backups on secondary infrastructure (Not a DR): In this all you need is a secondary infrastructure to fall back to and backups being continously sent to this site.
