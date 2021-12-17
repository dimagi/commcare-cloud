# Migrate from File System backend to an S3 compatible backend

This can be to Riak CS, Minio, S3 or any S3 compatible service.

## Ensure that the S3 endpoint is up and accessible
If you are running the service locally make sure it is fully setup. If you are using S3 ensure that
you have configured the correct access to allow connections from the IPs where CommCare is running. 

## Send new writes to the S3 endpoint

1. Update settings in `environments/<env>/public.yml`:
  - `localsettings.BLOB_DB_MIGRATING_FROM_FS_TO_S3: True`
  - `s3_blob_db_enabled: yes`
  - `s3_blob_db_url: "<Endpoint URL e.g. https://s3.amazonaws.com>"`
  - `s3_blob_db_s3_bucket: '<bucket name>'`
2. Add/update settings in `environments/<env>/vault.yml`
   - `secrets.S3_ACCESS_KEY`
   - `secrets.S3_SECRET_KEY`
3. Deploy localsettings
    ```bash
    commcare-cloud <env> update-config
    ```
4. Restart CommCare services
   ```bash
   commcare-cloud <env> fab restart_services
   ```

{% include_relative _blobdb_backfill.md %}

## Flip to just the new backend
1. Make sure you've run the steps above to move all data to the new backend.
2. Update `environments/<env>/public.yml`
   - Remove `localsettings.BLOB_DB_MIGRATING_FROM_FS_TO_S3`
3. Deploy localsettings with
   ```
   cchq <env> update-config
   ```
4. Restart CommCare services
   ```bash
   commcare-cloud <env> fab restart_services
   ```
