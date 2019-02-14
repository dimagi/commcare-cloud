# 8. Blob Metadata Migration - part 1

**Date:** 2018-09-24

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This version of CommCare must be deployed before rolling out this change:
[d7a5ee92](https://github.com/dimagi/commcare-hq/commit/d7a5ee92d32f719e3e19c5841fdc7cecd2072985)


## Change Context
Blob metadata needs to be migrated from CouchDB to SQL. This migration
consists of a series of commands that will move the data in your environment.

## Details
This migration will consist of running a series of commands against
your cluster to migrate blob metadata from CouchDB to SQL.

## Steps to update
Before executing any shell commands, set the `ENV` variable to the name of the
CommCareHQ environment you are migrating.

```sh
ENV=your_environment_name
```

1. Start a new screen session on a server in your cluster:

   ```sh
   cchq $ENV ssh django_manage -t screen -S blobmeta
   ```

   If you get disconnected for any reason, you can reconnect with this command:

   ```sh
   cchq $ENV ssh django_manage -t screen -x blobmeta
   ```

   Do all of the following commands within this screen session

2. Create a directory for migration logs

   ```sh
   su ansible
   sudo mkdir /opt/data/blobmeta-migration-logs
   sudo chown -R cchq:cchq /opt/data/blobmeta-migration-logs
   exit
   ```

3. Prepare to run migration management command

   ```sh
   sudo -iu cchq
   ENV=YOUR_ENVIRONMENT_NAME
   cd ~/www/$ENV/current
   source python_env/bin/activate
   ```

4. Run the management command

   ```sh
   ./manage.py run_blob_migration migrate_metadata \
   --log-dir=/opt/data/blobmeta-migration-logs \
   --chunk-size=1000
   ```

   You should see some output similar to this:

   ```
   Processing XXXX documents: CommCareAudio, CommCareBuild, CommCareCase, CommCareCase-Deleted, CommCareCase-Deleted-Deleted, CommCareCase-deleted, CommCareImage, CommCareMultimedia, CommCareVideo, HQSubmission, InvoicePdf, SavedBasicExport, SubmissionErrorLog, XFormArchived, XFormDeprecated, XFormDuplicate, XFormError, XFormInstance, XFormInstance-Deleted…
   Migration log: /opt/data/blobmeta-migration-logs/migrate_metadata-blob-migration-20181024T205839Z.txt.0
   Processed 1/1 of XXXX documents in 0:00:00.137354 (3:24:21.179518 remaining)
   Processed 1000/1000 of XXXX documents in 0:00:04.532256 (0:06:40.030576 remaining)
   Processed 2000/2000 of XXXX documents in 0:00:09.425483 (0:06:51.206816 remaining)
   ...
   ```

   You will see several stages of similar output as different groups of document
   types are migrated. Finally at the end there may be a traceback and an error
   like this:

   ```
   django.db.utils.ProgrammingError: relation "icds_reports_icdsfile" does not exist
   ```

   You can ignore this error.

5. The migration is complete when the management command is finished running,
   either with no error or with the "icds_reports_icdsfile" does not exist error
   mentioned above. If any other error occurred, please copy the error output
   and submit a bug report. Do not terminate the screen session until the
   migration has completed.

6. Exit the screen session when the migration has completed:

   ```sh
   exit  # cchq session
   exit  # screen session
   ```
