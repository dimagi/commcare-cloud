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
- Transfer these two files to the new environment.


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
  - `./manage.py run_blob_import <filename.tar.gz>`
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

- If desired, configure rate limiting to throttle the backlog of pending form
  submissions to handle a dramatic spike in load.
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


# Troubleshooting

When transferring data for very large projects, you may run into infrastructural
issues with the dump and load process. This is somewhat unsurprising when you
consider that you're dealing with the project's entire lifetime of data in a
single pass. It may be helpful to break down the process into smaller pieces to
minimize the impact of any failures.

Blob data is already separated from everything else, which is advantageous,
given that it's likely to be the most voluminous source of data. The rest of the
data comes from four "dumpers" - `domain`, `toggles`, `couch`, and `sql`. You
may use `dump_domain_data`'s `--dumper` arg to run any one (or multiple) of
these independently. Each dumper also deals with a number of models, which you
can also filter. Before getting started, you should run `print_domain_stats` to
get an idea of where the project has data (even though it's not comprehensive).

`domain` and `toggles` are trivially small. Assuming the project is on the SQL
backend for forms and cases, the `couch` dumper is also _likely_ to be several
orders of magnitude smaller than `sql`. Possible exceptions to this are projects
with very large numbers of users, gigantic fixtures, or those which use data
forwarding, as they'll have a large number of `RepeatRecord`s. If any of these
models reach into the six figures or higher, you might want to dump them in
isolation using `--include`, then `--exclude` them from the "everything else"
couch dump. If you don't care about a particular model (eg: old repeat records),
they can simply be excluded.

```
$ ./manage.py dump_domain_data --dumper=couch --include=RepeatRecord <domain>
$ ./manage.py dump_domain_data --dumper=domain --dumper=toggles --dumper=couch --exclude=RepeatRecord <domain>
```

Dumping `sql` data is a bit trickier, as it's relational, meaning for example
that `SQLLocation` and `LocationType` must be dumped together, lest they violate
the DB's constraint checking on import. Fortunately, as of this writing, the
biggest models are in relative isolation. There are two form submission models
and six case models, but they don't reference each other or anything else. You
should validate that this is still the case before proceeding, however. Here are
some example dumps which separate out forms and cases.

```
$ ./manage.py dump_domain_data --dumper=sql --include=XFormInstanceSQL --include=XFormOperationSQL <domain>
$ ./manage.py dump_domain_data --dumper=sql --include=CommCareCaseSQL --include=CommCareCaseIndexSQL --include=CaseAttachmentSQL --include=CaseTransaction --include=LedgerValue --include=LedgerTransaction <domain>
$ ./manage.py dump_domain_data --dumper=sql --exclude=XFormInstanceSQL --exclude=XFormOperationSQL --exclude=CommCareCaseSQL --exclude=CommCareCaseIndexSQL --exclude=CaseAttachmentSQL --exclude=CaseTransaction --exclude=LedgerValue --exclude=LedgerTransaction <domain>
```

You may also want to separate out `BlobMeta` or `sms` models, depending on the project.

If the data was already split into multiple dump files, then you can just load
them each individually. If not, or if you'd like to split it apart further,
you'll need to filter the `load_domain_data` command as well. Each dump file is
a zip archive containing a file for each dumper, plus a `meta.json` file
describing the contents. This can be useful for deciding how to approach an
unwieldly import. You can also specify which loaders to use with the `--loader`
argument (`domain`, `toggles`, `couch`, `sql`). You can also provide a regular
expression to filter models via the `--object-filter` argument. Refer to the
`meta.json` for options.

Here are some useful examples:

```
# Import only Django users:
$ ./manage.py load_domain_data path/to/dump.zip --object-filter=auth.User

# Import a series of modules' models
$ ./manage.py load_domain_data path/to/dump.zip --object-filter='\b(?:data_dictionary|app_manager|case_importer|motech|translations)'

# Exclude a specific model
$ ./manage.py load_domain_data path/to/dump.zip --object-filter='^((?!RepeatRecord).)*$'
```

Lastly, it's very helpful to know how long commands take. They run with a
progress bar that should give an estimated time remaining, but I find it also
helpful to wrap commands with the unix `date` command:

```
$ date; ./manage.py <dump/load command>; date
```
