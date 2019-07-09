# Backup and Restore

This page describes some of the backup options that can be accessed through CommCare cloud.

## Warning

You should read this section carefully and understand what each of these settings does. Backups are system dependent, and you should convince yourself that they are working correctly and that you are properly able to restore from them before something bad happens.

------

Each primary data-store that CommCareHQ uses can have backups turned on or off based settings in [`public.yml`](./env/index.md#publicyml) or the vault file. All settings mentioned below are to be placed in `public.yml` unless otherwise specified.

After making changes to these settings you will need to run:

``` bash
$ commcare-cloud <env> deploy-stack --tags=backups
```

## Backup to Amazon S3 or a compatible service

`commcare-cloud` has the ability to upload all backups automatically for storage on Amazon S3 or an S3-compatible alternative. Each service's backup has a specific setting that needs to be enabled for this to happen, as detailed below.

### S3 credentials
In order to use this service, you will need to add your S3 credentials to the `localsettings_private` section of your **[vault file](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/README.md#managing-secrets-with-vault)**:

- `AMAZON_S3_ACCESS_KEY`: Your aws access key id
- `AMAZON_S3_SECRET_KEY`: Your aws secret access key

Even though these settings have the word `AMAZON` in them, you should use use the credentials of your S3-compatible hosting provider.

### Endpoints
We use [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html?id=docs_gateway) to upload data to Amazon S3 or a compatible service.

- `aws_endpoint`: The endpoint to use. Add this setting if you are using an S3-compatible service that isn't AWS.
- `aws_region`: The Amazon AWS region to send data to. (Amazon S3 only - this changes the default aws-endpoint to the region-specific endpoint).
- `aws_versioning_enabled`: (`true` or `false`) Set this to `true` if the AWS endpoint you are using automatically stores old versions of the same file (Amazon S3 does this). If this is set to `false`, files will be uploaded to your S3-compatible bucket with a date and timestamp in the filename, creating a new file each time. (Default: `true`)

## PostgreSQL Backups

PostgreSQL backups are made daily and weekly. Old backups are deleted from the local system.

- `postgresql_backup_dir`: The directory to write the PostgreSQL backups to. (Default: `/opt/data/backups/postgresql`)
- The `backup_postgres` setting has a few options. You should understand the tradeoffs of each of these settings and know how to restore from the resulting backup files. 
    - `plain` - uses the [`pg_basebackup`](https://www.postgresql.org/docs/9.6/app-pgbasebackup.html) command to write a backup to the `postgresql_backup_dir`. 
    - `dump` - uses the [`pg_dumpall`](https://www.postgresql.org/docs/9.6/app-pg-dumpall.html) command to write a dump of the database to the `postgresql_backup_dir`.
- `postgres_backup_days`: The number of days to keep daily backups (Default: 1)
- `postgres_backup_weeks`: The number of weeks to keep weekly backups (Default: 1)

### Enabling S3 backups for PostgreSQL

After [adding your credentials](#amazon-s3-credentials) to the vault file, set:

- `postgres_s3: True`
- `postgres_snapshot_bucket`: The name of the S3 bucket to save postgres backups to (Default: `dimagi-<env>-posgres-backups`).

### Restoring PostgreSQL Backups

You should first stop all CommCareHQ services:

``` bash
$ commcare-cloud <env> downtime start
```

Restoring from backup depends on the type of backup made.

#### plain (`pg_basebackup`) without S3

If you are using a `pg_basebackup`, you should follow these [instructions](https://www.postgresql.org/docs/9.6/continuous-archiving.html#BACKUP-PITR-RECOVERY). The latest daily backup should be in the directory specified in `postgresql_backup_dir`, above. 

For example, you can follow a process similar to this one:

- You will need to run commands as the `postgres` user:

    ``` bash
    $ su - ansible
    # enter ansible user password from vault file
    $ sudo -u posgres bash
    # enter ansible user password again. You will now be acting as the posgres user
    ```

- Find the list of current backups and choose the one you want to restore from, for e.g.:

    ``` bash 
    $ ls -la /opt/data/backups/postgresql # or whatever your postgres backup directory is set to 
    total 3246728
    drwxr-xr-x 2 postgres postgres      4096 Jul  8 00:03 .
    drwxr-xr-x 5 root     root          4096 Feb  6  2018 ..
    -rw-rw-r-- 1 postgres postgres 678073716 Jul  6 00:03 postgres_<env>_daily_2019_07_06.gz
    -rw-rw-r-- 1 postgres postgres 624431164 Jun 23 00:03 postgres_<env>_weekly_2019_06_23.gz
    ```
- Uncompress the one you want:
    ``` bash
    $ tar -xjf /opt/data/backups/posgresql/postgres_<env>_daily_2019_07_06.gz -C /opt/data/backups/postgresql
    ```
    
- [Optional] Make a copy of the current data directory, for eg:

    ```bash
    $ tar -czvf /opt/data/backups/postgresql/postgres_data_before_restore.tar.gz /opt/data/posgresql/9.6/main
    ```

-  Copy backup data to the postgres data directory. This will overwrite all the data in this directory.

    ``` bash
    $ rsync -avz --delete /opt/data/backups/posgresql/postgres_<env>_daily_2019_07_06 /opt/data/posgresql/9.6/main
    ```

- Restart Postgres and services, from the control machine, e.g.:

    ``` bash
    $ commcare-cloud <env> service postgresql start
    ```

#### plain (`pg_basebackup`) with S3

If you have S3 backups enabled there is a [restore script](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/roles/pg_backup/templates/plain/restore_from_backup.sh.j2) that was installed when the system was installed. 

On the PostgreSQL machine:

- Become the root user
    ``` bash
    $ su - ansible
    # enter ansible user password from vault file
    $ sudo -u root bash
    # enter ansible user password again. You will now be acting as the root user
    ```

- Run the restore script after finding the backup you want to restore from S3
    ``` bash
    $ restore_from_backup <name of backup file>
    ```

**Note:** this script will not make a copy of the current data directory and should be used with caution. You should know and understand what this script does before running it. 

#### dump (`pg_dumpall`)

You should follow [these instructions](https://www.postgresql.org/docs/9.6/backup-dump.html#BACKUP-DUMP-ALL) to restore from a dump. You will need to have a new database set up with a root user as described in the instructions.

## CouchDB backups

CouchDB backups are made daily and weekly. Old backups are deleted from the system.

- `backup_couch: True` to enable couchdb backups (Default: `False`)
- `couch_s3: True` to enable sending couchdb backups to your S3 provider (Default: `False`)
- `couch_backup_dir`: the directory to save backups in (Default: `/opt/data/backups/couchdb2`)
- `couchdb_backup_days`: The number of days to keep daily backups (Default: 1)
- `couchdb_backup_weeks`: The number of weeks to keep weekly backups (Default: 1)

CouchDB backups create a compressed version of the couchdb data directory.

### Restoring CouchDB backups

Restoring couchdb from a backup simply requires stopping couchdb, overwriting the current data directory with the contents of the backup files, then restarting couchdb.

- From the control machine, stop all running services:

    ``` bash
    $ commcare-cloud <env> downtime start
    ```

- From the couchdb machine, become the couchdb user:
    ``` bash
    $ su - ansible
    # enter ansible user password from vault file
    $ sudo -u couchdb bash
    # enter ansible user password again. You will now be acting as the couchdb user
    ```
- [Optional] Copy the contents of the current couchdb directory in case anything goes wrong. From the couchdb machine:

    ``` bash
    $ tar -czvf /opt/data/backups/couchdb2/couchdb_data_before_restore.tar.gz /opt/data/couchdb2/
    ```

- Uncompress the backup you want, e.g:

    ``` bash
    $ tar -xjf /opt/data/backups/couchdb2/couchdb2_<env>_daily_2019_07_06.gz -C /opt/data/backups/couchdb
    ```

-  Copy backup data to the couchdb data directory. This will overwrite all the data in this directory.

    ``` bash
    $ rsync -avz --delete /opt/data/backups/couchdb2/couchdb2_<env>_daily_<date> /opt/data/couchdb2
    ```

- Start couchdb again (from the control machine):

    ``` bash
    $ commcare-cloud <env> service couchdb2 start
    ```

## BlobDB Backups

The `blobdb` is our binary data store. 

- `backup_blobdb: True`:  to enable blobdb backups
- `blobdb_s3: True`: to enable sending blobdb backups to S3
- `blobdb_backup_dir`: the directory to write blobdb backups to (Default: `/opt/data/backups/blobdb`)
- `blobdb_backup_days`: the number of days to keep daily backups (Default: 2)
- `blobdb_backup_weeks`: the number of weeks to keep weekly backups (Default: 2)

BlobDB backups create a compressed version of the blobdb data directory.

### Restoring BlobDB Backups

You can follow the same instructions as for [restoring couchdb](#restoring-couchdb-backups) (extract the backup file into the blobdb data directory: `/opt/data/blobdb/`). 

The files in the resulting directory should all be owned by the user `cchq` (i.e. you should be the `cchq` user when extracting the files)

## Elasticsearch Snapshots

While it is possible to backup Elasticsearch data, it isn't always necessary as this is not a primary data store and can be rebuilt from primary sources. If Elasticsearch data is lost or deleted in entirety, it will be recreated when a [deploy is made](./deploy.md) to the cluster.

However, you may still back-up Elasticsearch using [Elasticsearch Snapshots](https://www.elastic.co/guide/en/elasticsearch/reference/1.7/modules-snapshots.html#_snapshot) directly to S3 or locally. The rest of this section assumes an understanding of that documentation page.

- `backup_es_s3: True`:  to create snapshots and send them directly to S3 (not stored locally)
- `es_local_repo: True`: to save snapshots locally (not sent to S3)
- `es_repository_name`: the name to give to the snapshot respository
- 

Both of those settings are **mutually exclusive**. There is currently no way to create snapshots to be saved locally and sent to S3 at the same time.

### Restoring Elasticsearch Snapshots

You can restore snapshots by following the [instructions given by Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/1.7/modules-snapshots.html#_restore)
