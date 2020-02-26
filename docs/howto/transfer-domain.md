# Transfer a Project From a Multi-tenant to Standalone Environment

This document describes the process of migrating a project from Dimagi's cloud
environment to a new, single-project environment.

This process requires assistance from Dimagi, as some steps require
administrative access to the old environment. To initiate, reach out to Dimagi
or file a support request.

## 1. Switch mobile devices to a proxy URL

Each application maintains a series of URLs used for the various requests made
by the mobile devices. Since rolling out an app update to all mobile devices
takes time, it's best to not rely on that when switching server environments.
Instead, we direct apps to a custom URL which directs requests to the original
server, then after the migration, to the new server. This switch happens at the
DNS level, without requiring a change on each device.

- Set up a domain name to be used for the migration. Have it point to the old
   environment.
- Add that domain name to the old environment's public.yml:
   ```
   ALTERNATE_HOSTS:
     - commcare.example.com
   ```
- Update the list of valid hosts in nginx and Django, then restart services for
   it to take effect.  After this, CommCareHQ should be accessible at the new
   domain name.
   ```
   $ cchq <env> ansible-playbook deploy_proxy.yml
   $ cchq <env> update-config
   $ cchq <env> fab restart_services
   ```
- Enable the feature flag `CUSTOM_APP_BASE_URL` for the project. This will need
   to be done by a site administrator.
- For each app in the project, navigate to Settings > Advanced Settings, and
   enter in the domain name you created above.
- Make a new build and test it out to ensure form submissions and syncs still
   work as usual.
- Release the build and roll it out to all users.

That is, there are three registered domain names, which I'll call "old", "new",
and "mobile". This table describes which domain name each type of user will
access at each stage of the migration:

|                 | web users         | mobile workers                        |
|-----------------|-------------------|---------------------------------------|
| current state   | access old domain | access old domain                     |
| pre-migration   | access old domain | access mobile domain as alias for old |
| during downtime | access blocked    | access mobile domain, but blocked     |
| post-migration  | access new domain | access mobile domain as alias for new |
| after clean-up  | access new domain | access new domain directly            |


## 2. Pull the domain data from the old environment

The migration will require you to block data access to prevent loss of data
created during the migration. In spite of this, a practice run may also be done
without this data freeze, though the data will need to be cleared before the
real run.

During the downtime, mobile users will still be able to collect data, but they
will be unable to submit forms or sync with the server.

- Block data access by turning on the `DATA_MIGRATION` feature flag.
- Print information about the numbers in the database for later reference.
  This will take a while (15 mins) even on small domains. Tip: add `--csv` to
  the command to save the output in a csv file.
  - `./manage.py print_domain_stats <domain_name>`
- A site administrator will need to run the data dump commands. First run
  `$ df -h` to ensure the machine has the disk space to store the output. Then
  run the data dumps.
  - `./manage.py dump_domain_data <domain_name>` 
  - `./manage.py run_blob_export --all <domain_name>`
- Transfer these two zip files to the new environment.


## 3. Prepare the new environment to be populated

- Stop all services
  `$ commcare-cloud <env> downtime start`
- Delete any blob data
- Delete the PostgreSQL database
- Delete the CouchDB database
- Delete all elasticsearch indices
  - Figure out what the elasticearch IP is:
    `ES_IP=$(commcare-cloud ${ENV} lookup elasticsearch:0)`
  - Go ahead and check the size of the forms index to make sure this is the
    correct cluster.  Be VERY sure this is correct.
    `curl -XGET "${ES_IP}:9200/xforms/_stats/docs?pretty`
  - Delete all elasticsearch data in that cluster
    `curl -X DELETE ${ES_IP}:9200/_all?pretty`
- Clear the redis cache data
  `./manage.py flush_caches`
- Clear kafka


## 4. Import the data to the new environment

- Import the dump files (each blob file will need to be imported individually)
  - `./manage.py load_domain_data <filename.zip>`
  - `./manage.py import_blob_zip <filename.zip>`
- Rebuild elasticsearch indices
  - Rebuild the indices with the new data
    `./manage.py ptop_preindex`
    `./manage.py ptop_es_manage --flip_all_aliases`
- Print the database numbers and compare them to the values obtained previously
  - `./manage.py print_domain_stats <domain_name>`
- Rebuild case ownership cleanliness flags
  - `./manage.py set_cleanliness_flags --force <domain_name>`
- Bring the site back up
  `$ commcare-cloud <env> downtime end`


## 5. Ensure the new environment is fully functional. Test all critical workflows at this stage.

- Check reports and exports for forms and cases migrated from the old environment.
- Download the application with a test user and submit some forms.
- Ensure that those new form submissions appear in reports and exports.
- Make a change to the application and ensure that it can be built.


## 6. Turn on the new environment

- Change the DNS entry for the proxy URL to point to the new environment. This
  will cause mobile devices to contact the new servers, bringing them back
  on-line.
- The new site should now be ready for use. Instruct web users to access the new
  URL.
- The old domain should remain disabled for a while to avoid confusion.


## 7. Clean up

- Switch mobile devices to the new environment's URL. Reverse the steps taken
   previously, since the custom URL is no longer necessary.
- Once the success of the migration is assured, request that a site
   administrator delete the project space on the old environment.
