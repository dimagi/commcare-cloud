.. _migrate-project:

Migrate a CommCare Application from one instance to a new instance
==================================================================
.. note::
  This guide is for projects which do not require a full project migration and are only interested in
  migrating an existing CommCare application from one CommCare HQ instance to another CommCare HQ instance.
  In the event that you already did a full project migration as outline in :doc:`/installation/migration/1-migrating-project`, this guide
  will not be relevant anymore.


Often application development commences on the Dimagi-hosted CommCare HQ environment
(referred to as an “upstream domain”) in parallel with deploying an on-premise instance
of CommCare (referred to as an “downstream domain”. The application code must be moved to the
on-premise instance of CommCare so that it can be pushed to end users’ devices.
This is achieved by doing a one-time migration of the application from the Dimagi-hosted environment to the
on-premise instance before severing the link.


1. Prerequisites
----------------
In order to proceed with establishing the link between each domain, the following must be established:

1. A CommCare administrative user must have access to both the upstream and downstream project spaces

2. The CommCare administrative user must have the Multi-Environment Release Management permission added
   to their role in both the upstream and downstream domains.

3. Each downstream project space must have the “Linked Project Space” project setting enabled.


2. Process
----------
Once the prerequisites have been met you must:

1. Run the `link_to_upstream_domain` management command on the downstream environment in order to link
   the upstream environment to the downstream environment.

2. Sync the downstream environment with the upstream environment by going to
   Project Settings -> Linked Project Spaces -> select Sync & Overwrite for all the content wished to be
   copied to this downstream environment

3. Create a new “empty” application in the downstream project

4. Run the `link_app_to_remote` management command in the downstream environment in order to link the new
   downstream application to the upstream application

5. Update the downstream application by clicking the Update button when selecting this application from
   the UI on the downstream environment.

6. Run the `unlink_apps` management command to cut the link between the upstream and downstream environments

Your CommCare application should now be a fully functional standalone application on the downstream CommCare HQ instance.
