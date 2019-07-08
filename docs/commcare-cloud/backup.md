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

## Backup to Amazon S3 or compatible service

`commcare-cloud` has the ability to upload all backups automatically for storage on Amazon S3. Each backup service has a specific setting that needs to be enabled for this to happen, as detailed below.

### Amazon S3 credentials
In order to use this service, you will need to add your S3 credentials to the `localsettings_private` section of your **[vault file](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/README.md#managing-secrets-with-vault)**:

- `AMAZON_S3_ACCESS_KEY`: Your aws access key id
- `AMAZON_S3_SECRET_KEY`: Your aws secret access key

### Endpoints
We use [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html?id=docs_gateway) to upload data to Amazon S3 or a compatible service.

- `aws_endpoint`: The endpoint to use. Change this if you are using an S3 compatible service that isn't Amazon's.
- `aws_region`: The aws region to send data to. 
- `aws_versioning_enabled`: (`true` or `false`) Set this to `true` if the AWS endpoint you are using automatically stores old versions of the same file. If this is set to `false`, files will be uploaded to your S3 bucket with a date and timestamp in the filename. (Default: `true`)

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

Restoring from backup depends on the type of backup made.

#### plain (`pg_basebackup`)

If you are using a `pg_basebackup`, you should follow these [instructions](https://www.postgresql.org/docs/9.6/continuous-archiving.html#BACKUP-PITR-RECOVERY). The latest daily backup should be in the directory specified in `postgresql_backup_dir`, above. 

If you have S3 backups enabled there is a [restore script](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/roles/pg_backup/templates/plain/restore_from_backup.sh.j2) that was installed when the system was installed. On the PostgreSQL machine, run:

``` shell
$ sudo restore_from_backup
```
Note: this script will not make a copy of the current data directory and should be used with caution. You should know and understand what this script does before running it. 

#### dump (`pg_dumpall`)

You should follow [these instructions](https://www.postgresql.org/docs/9.6/backup-dump.html#BACKUP-DUMP-ALL) to restore from a dump. You will need to have a new database set up with a root user as described in the instructions.
