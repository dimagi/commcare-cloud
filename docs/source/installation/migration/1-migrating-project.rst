.. _migrate-project:

Migrate a Project from one instance to a new instance
=====================================================

This document describes the process of migrating an individual project from Dimagi's cloud
environment (or any other environment) to a new environment. If you are looking to migrate
the entire environment to the new environment please see :ref:`migrate-instance`.

This process requires assistance from Dimagi if migrating from www.commcarehq.org, 
as some steps require administrative access to the old environment. To do that, 
reach out to Dimagi or file a support request.

There are two components to migrate an individual project.

1. Migrating the project specific data to the new environment. This is done using export and import data functionalities
   in CommCare HQ.
2. Switching the mobile devices with CommCare apps to use the new environment. This is done using a interim proxy URL
   for mobile devices.

Note that during the export/import data phase the access to the project has to be disabled for mobile and web users, 
which might take considerable amount of time. This should be planned and communicated in advance for a smooth
switchover to the new environment.

1. Switch mobile devices to a proxy URL
---------------------------------------

Each application maintains a series of URLs pointing to CommCare HQ environment used for
various requests made by the mobile devices. Migrating to a new web address requires updating these
URLs in all the mobile devices at the time of switching the environments after the data is migrated. Since rolling out an app update to every mobile device of the project
takes time during which the site needs to be offline, it will result in a long downtime for the project. Hence, if your project has any more than a couple of devices, it's best not to do it this way.

Instead, before the migration itself, a new/proxy URL can be set up and configured to direct requests
to the original environment and the mobile devices can be gradually updated to use the new URL while
the project is still online. Then after the migration, the URL can be switched to the new environment.
The URL switch happens at the DNS level, so an app update is not needed. Note that, an all device
update is still required in this method, but the advantage is that it can be done before the migration.

.. note::
  Mobile devices should be switched to the proxy URL well in advance of doing the data migration so as to make sure all mobile users updated their applications!

To do this, follow the below steps.

#. Set up a domain name to be used for the migration. Have it point to the old environment.
#. Add that domain name to the old environment's public.yml

   .. code-block::

      ALTERNATE_HOSTS:
        - commcare.example.com

#. Update the list of valid hosts in nginx and Django, then restart services for
   it to take effect.  After this, CommCare HQ should be accessible at the new
   domain name.

   .. code-block::

      $ cchq <env> ansible-playbook deploy_proxy.yml
      $ cchq <env> update-config
      $ cchq <env> service commcare restart

#. Set up SSL certificate for the domain name.
#. Enable the feature flag ``CUSTOM_APP_BASE_URL`` for the project. This will need
   to be done by a site administrator.
#. For each app in the project, navigate to Settings > Advanced Settings, and
   enter in the domain name you created above.
#. Make a new build and test it out to ensure form submissions and syncs still
   work as usual.
#. Release the build and roll it out to all devices. You can refer to Application Status Report
   to make sure that all the mobile devices are using this build.

If you don't want to use the final domain to point to old environment, a different
domain can also be used during migration.
That is, there are three registered domain names, which can be called "old", "new",
and "mobile". This table describes which domain name each type of user will
access at each stage of the migration:

.. list-table::
   :header-rows: 1

   * - 
     - web users
     - mobile workers
   * - current state
     - access old domain
     - access old domain
   * - pre-migration
     - access old domain
     - access mobile domain as alias for old
   * - during downtime
     - access blocked
     - access mobile domain, but blocked
   * - post-migration
     - access new domain
     - access mobile domain as alias for new
   * - after clean-up
     - access new domain
     - access new domain directly

Only after all the devices are updated to use a new/mobile URL, you can proceed to the next step.

2. Pull the domain data from the old environment
------------------------------------------------

The migration will require you to block data access to prevent loss of data created during the migration. If you
would like to do a practice run, you will still need to block data access to ensure the exported data is in a
clean state, and the data will need to be cleared before the real run.

During the downtime, mobile users will still be able to collect data, but they
will be unable to submit forms or sync with the server.


* Block data access by turning on the ``DATA_MIGRATION`` feature flag (via HQ Web UI).
* Print information about the numbers in the database for later reference.
  This will take a while (15 mins) even on small domains. Tip: add ``--csv`` to
  the command to save the output in a csv file.

  * ``./manage.py print_domain_stats <domain_name>``

* A site administrator will need to run the data dump commands. First run
  ``$ df -h`` to ensure the machine has the disk space to store the output. Then
  run the data dumps.

  * ``./manage.py dump_domain_data <domain_name>`` 
  * ``./manage.py run_blob_export --all <domain_name>``

  .. note::
     It is important to have the commit hash that ``dump_domain_data`` and ``run_blob_export`` were run from. If
     Dimagi does not provide you with this commit hash, please followup to ensure you are able to reference this
     hash in future steps.

* Transfer these files to the new environment.

.. note::
  If you are not able to use your own domain for a test run and would like dump data for a test domain for
  practising or testing, please contact support with the subject "Request for test domain dump data for migration
  testing" and mention this page. We will provide you the above data for a test domain from our staging
  environment.


3. Prepare the new environment to be populated
----------------------------------------------

* Ensure you are running the following steps from a release created using the CommCare version/commit hash that you
  should have been provided in Step 1. This ensures the database will be migrated to the same state it was in when
  the data was dumped.
* Setup a new environment by following :ref:`deploy-commcarehq`
* Follow steps in 
  :ref:`reference/howto/wipe_persistent_data:How To Rebuild a CommCare HQ environment`
  to ensure your environment is in a clean state before attempting to import data.
* Proceed to step 4.


.. _import-data-into-environment:

4. Import the data to the new environment
-----------------------------------------

* Ensure you are running the following steps from a release created using the CommCare version/commit hash that you
  should have been provided in Step 1. This ensures the database will be migrated to the same state it was in when
  the data was dumped.

* Import the dump files (each blob file will need to be imported individually)

  * ``./manage.py load_domain_data <filename.zip>``
  * ``./manage.py run_blob_import <filename.tar.gz>``

* Rebuild elasticsearch indices

  * Rebuild the indices with the new data
    ``./manage.py ptop_preindex --reset``

* Print the database numbers and compare them to the values obtained previously

  * ``./manage.py print_domain_stats <domain_name>``

* Rebuild user configrable reports by running.

  * ``./manage.py rebuild_tables_by_domain <domain_name> --initiated-by=<your-name>``

* Bring the site back up
  ``$ commcare-cloud <env> downtime end``

* Enable domain access by turning off the ``DATA_MIGRATION`` feature flag on the new environment (via HQ Web UI).


5. Ensure the new environment is fully functional. Test all critical workflows at this stage.
---------------------------------------------------------------------------------------------


* Check reports and exports for forms and cases migrated from the old environment.
* Download the application with a test user and submit some forms.
* Ensure that those new form submissions appear in reports and exports.
* Make a change to the application and ensure that it can be built.

6. Turn on the new environment
------------------------------


* If desired, configure rate limiting to throttle the backlog of pending form
  submissions to handle a dramatic spike in load.
* Change the DNS entry for the proxy URL to point to the new environment. This
  will cause mobile devices to contact the new servers, bringing them back
  on-line.
* The new site should now be ready for use. Instruct web users to access the new
  URL.
* The old domain should remain disabled for a while to avoid confusion.

7. Clean up
-----------


* Switch mobile devices to the new environment's URL. Reverse the steps taken
  previously, since the custom URL is no longer necessary.
* Once the success of the migration is assured, request that a site
  administrator delete the project space on the old environment.

Troubleshooting
---------------

When transferring data for very large projects, you may run into infrastructural
issues with the dump and load process. This is somewhat unsurprising when you
consider that you're dealing with the project's entire lifetime of data in a
single pass. It may be helpful to break down the process into smaller pieces to
minimize the impact of any failures.

Blob data is already separated from everything else, which is advantageous,
given that it's likely to be the most voluminous source of data. The rest of the
data comes from four "dumpers" - ``domain``\ , ``toggles``\ , ``couch``\ , and ``sql``. You
may use ``dump_domain_data``\ 's ``--dumper`` arg to run any one (or multiple) of
these independently. Each dumper also deals with a number of models, which you
can also filter. Before getting started, you should run ``print_domain_stats`` to
get an idea of where the project has data (even though it's not comprehensive).

``domain`` and ``toggles`` are trivially small. Assuming the project is on the SQL
backend for forms and cases, the ``couch`` dumper is also *likely* to be several
orders of magnitude smaller than ``sql``. Possible exceptions to this are projects
with very large numbers of users, gigantic fixtures, or those which use data
forwarding, as they'll have a large number of ``RepeatRecord``\ s. If any of these
models reach into the six figures or higher, you might want to dump them in
isolation using ``--include``\ , then ``--exclude`` them from the "everything else"
couch dump. If you don't care about a particular model (eg: old repeat records),
they can simply be excluded.

.. code-block::

   $ ./manage.py dump_domain_data --dumper=couch --include=RepeatRecord <domain>
   $ ./manage.py dump_domain_data --dumper=domain --dumper=toggles --dumper=couch --exclude=RepeatRecord <domain>

Dumping ``sql`` data is a bit trickier, as it's relational, meaning for example
that ``SQLLocation`` and ``LocationType`` must be dumped together, lest they violate
the DB's constraint checking on import. Fortunately, as of this writing, the
biggest models are in relative isolation. There are two form submission models
and six case models, but they don't reference each other or anything else. You
should validate that this is still the case before proceeding, however. Here are
some example dumps which separate out forms and cases.

.. code-block::

   $ ./manage.py dump_domain_data --dumper=sql --include=XFormInstanceSQL --include=XFormOperationSQL <domain>
   $ ./manage.py dump_domain_data --dumper=sql --include=CommCareCaseSQL --include=CommCareCaseIndexSQL --include=CaseAttachmentSQL --include=CaseTransaction --include=LedgerValue --include=LedgerTransaction <domain>
   $ ./manage.py dump_domain_data --dumper=sql --exclude=XFormInstanceSQL --exclude=XFormOperationSQL --exclude=CommCareCaseSQL --exclude=CommCareCaseIndexSQL --exclude=CaseAttachmentSQL --exclude=CaseTransaction --exclude=LedgerValue --exclude=LedgerTransaction <domain>

You may also want to separate out ``BlobMeta`` or ``sms`` models, depending on the project.

If the data was already split into multiple dump files, then you can just load
them each individually. If not, or if you'd like to split it apart further,
you'll need to filter the ``load_domain_data`` command as well. Each dump file is
a zip archive containing a file for each dumper, plus a ``meta.json`` file
describing the contents. This can be useful for deciding how to approach an
unwieldly import. You can also specify which loaders to use with the ``--loader``
argument (\ ``domain``\ , ``toggles``\ , ``couch``\ , ``sql``\ ). You can also provide a regular
expression to filter models via the ``--object-filter`` argument. Refer to the
``meta.json`` for options.

Here are some useful examples:

.. code-block::

   # Import only Django users:
   $ ./manage.py load_domain_data path/to/dump.zip --object-filter=auth.User

   # Import a series of modules' models
   $ ./manage.py load_domain_data path/to/dump.zip --object-filter='\b(?:data_dictionary|app_manager|case_importer|motech|translations)'

   # Exclude a specific model
   $ ./manage.py load_domain_data path/to/dump.zip --object-filter='^((?!RepeatRecord).)*$'

Lastly, it's very helpful to know how long commands take. They run with a
progress bar that should give an estimated time remaining, but I find it also
helpful to wrap commands with the unix ``date`` command:

.. code-block::

   $ date; ./manage.py <dump/load command>; date
