# Migrate from one S3 backend to another

This can be from one Riak CS cluster to another,
or from a Riak CS cluster to Amazon S3, for example.

## Send new writes to the new S3 endpoint

1. If the new endpoint is a riakcs cluster,
   add `[riakcs_new]` hosts (of new riak cluster) to inventory.
   (Otherwise skip this step.)
2. Add `localsettings.BLOB_DB_MIGRATING_FROM_S3_TO_S3: True`
   in `environments/<env>/public.yml`
3. Add/update settings in `environments/<env>/vault.yml`
   - `secrets.RIAKCS_S3_ACCESS_KEY` (new cluster)
   - `secrets.RIAKCS_S3_SECRET_KEY` (new cluster)
   - `secrets.OLD_S3_BLOB_DB_ACCESS_KEY` (old cluster)
   - `secrets.OLD_S3_BLOB_DB_SECRET_KEY` (old cluster)
4. If the new endpoint is a Riak CS cluster, deploy proxy.
   This will leave the proxy site for the old endpoint listing to port 8080,
   and add a new one listening to 8081. (If migrating to Amazon S3, can skip.)
    ```bash
    commcare-cloud <env> ansible-playbook deploy_proxy.yml
    ```
5. Deploy localsettings
    ```bash
    commcare-cloud <env> update-config
    ```
   During this deploy hosts with old localsettings will continue to talk
   to old riak cluster on port 8080.

## Back-fill all existing data

After things are set up to read from the new backend and fall back to the old backend,
you'll need to run some commands to migrate all existing data
from the old backend to the new backend.

First, make sure that the directory you'll use for logs exists:

```
cchq <env> run-shell-command django_manage 'mkdir /opt/data/riak2s3-migration-logs; chown cchq:cchq /opt/data/riak2s3-migration-logs' -b
```

Then run the migration in a tmux (or screen) with these good defaults options
(you can tweak the options if you know what you're doing):
```
cchq <env> django-manage --tmux run_blob_migration migrate_backend --log-dir=/opt/data/riak2s3-migration-logs --chunk-size=1000 --num-workers=15
```

At the end, you may get a message saying that some blobs are missing
and a link to a log file that contains the info about which ones.
(If you don't get this message, congratulations! You can skip this step.)
Run the following command to check all the blobs in the file to get more info
about their status (the last arg is the log file that was printed out above):

```
cchq india django-manage --tmux check_blob_logs /opt/data/riak2s3-migration-logs/migrate_backend-blob-migration-<timestamp>.txt```
```

The output will look something like this:

```
tempfile: checked 2342 records
  Found in new db: 0
  Found in old db: 0
  Not referenced: 0
  Not found: 2342
XFormInstance: checked 42 records
  Found in new db: 0
  Found in old db: 0
  Not referenced: 21
  Not found: 21
...
```

Legend:
- `Not referenced` is OK. It means that the blob that was said to be "missing"
  isn't in the blobdb but also isn't referenced by its parent object anymore (this is only meaningful if `BlobMeta.parent_id` is a couch identifier that can be used to lookup the parent object), so it was likely deleted
  while the migration was running.
- `Not found` means that the missing blob is still referenced in blob metadata,
  but not found in either the old backend or new backend.
- `Found in (new|old) db` means that actually it is present in one of the backends,
  unlike originally reported. Re-run the `check_blob_logs` command with `--migrate` to migrate items "Found in old db".

## Flip to just the new backend
1. Make sure you've run the steps above to move all data to the new backend.
2. Move `[riakcs_new]` hosts to `[riakcs]` (and delete old hosts) in inventory
3. Update `environments/<env>/public.yml`
   - Remove `localsettings.BLOB_DB_MIGRATING_FROM_S3_TO_S3: True`
   - Add    `localsettings.TEMP_RIAKCS_PROXY: True`
4. Deploy proxy with
   ```
   cchq <env> ansible-deploy deploy_proxy.yml --tags=nginx_sites 
   ```
   You should see both ports (8080 and 8081) now route to the new blobdb backend.
5. Deploy localsettings with
   ```
   cchq <env> update-config
   ```
   During this deploy hosts with old localsettings will continue to talk
   to new riak cluster on port 8081, and once updated will talk to new riak
   cluster proxied on port 8080. There is a slight chance of MigratingBlobDB
   failover from new to new, but this should be rare and benign.
6. Remove `localsettings.TEMP_RIAKCS_PROXY: True` from `environments/<env>/public.yml`
7. Deploy proxy again with
   ```
   cchq <env> ansible-deploy deploy_proxy.yml --tags=nginx_sites 
   ```
   You should now see only 8080 route to the new blobdb backend,
   with the configuration for 8081 being removed.
