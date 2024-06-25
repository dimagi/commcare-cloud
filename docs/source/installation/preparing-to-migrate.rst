Preparing to Migrate
====================

If you are migrating to your new environment from an existing
environment, it is important that mobile users experience as little
disruption as possible.

You can minimize disruption by preparing the following in advance:

#. Register a DNS alias that initially points to the existing
   environment. This is most likely to be Dimagi's production
   environment, www.commcarehq.org.

#. Set the DNS alias as a custom base URL for each CommCare application
   that is in use, and build and release a new version.

#. Depending on the nature of the project, deploying a new app version
   can be time consuming. Your planning will need to take this into
   consideration. Ensure that all CommCare apps with custom base URLs
   are deployed and in use before the start of the migration.

Once the migration is complete, you can update the DNS alias to point to
the new environment. When that is done mobile workers will be able to
submit forms and sync data.
