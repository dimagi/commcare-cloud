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

1. Run migration to copy objects from old to new S3 backend
2. Move `[riakcs_new]` hosts to `[riakcs]` (and delete old hosts) in inventory
3. Update `environments/<env>/public.yml`
   - Remove `localsettings.BLOB_DB_MIGRATING_FROM_S3_TO_S3: True`
   - Add    `localsettings.TEMP_RIAKCS_PROXY: True`
4. Deploy proxy (new=8080, new=8081)
5. Deploy localsettings.
   During this deploy hosts with old localsettings will continue to talk
   to new riak cluster on port 8081, and once updated will talk to new riak
   cluster proxied on port 8080. There is a slight chance of MigratingBlobDB
   failover from new to new, but this should be rare and benign.
6. Remove `localsettings.TEMP_RIAKCS_PROXY: True` from `environments/<env>/public.yml`
7. Deploy proxy (new=8080)
