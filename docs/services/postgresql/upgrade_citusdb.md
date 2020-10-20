# Upgrading CitusDB

1. Ensure that you have a full backup of all PostgreSQL data before starting the upgrade process.
2. Review the documentation:
    - [pg_upgrade](https://www.postgresql.org/docs/current/pgupgrade.html)
    - [citus](http://docs.citusdata.com/en/v9.4/admin_guide/upgrading_citus.html)
3. Test the upgrade process locally with Vagrant or on a test environment.

This upgrade is split into two parts:

1. Upgrade the 'citus' extension
2. Upgrade PostgreSQL

The citus extension should be upgraded prior to upgrading PostgreSQL.

In the below instructions:

    OLD-VERSION: Current version of PostgreSQL that is running
    NEW-VERSION: Version being upgraded to
    OLD-PORT: Port that PostgreSQL is currently running on (defaults to 5432)

## Upgrade 'citus'

### Prepare for the 'citus' extension upgrade

#### 1. Run the `deploy_citusdb.yml` playbook to ensure your system is up to date

    commcare-cloud <env> ap deploy_citusdb.yml

### Upgrade the 'citus' extension

#### 1. Update `public.yml`

public.yml:

```yaml
citus_version: <new citus version>
```

#### 2. Run the `deploy_citusdb.yml` playbook

    commcare-cloud <env> ansible-playbook deploy_citusdb.yml --tags citusdb

#### 3. Check the extension version

    commcare-cloud <env> run-shell-command citusdb -b --become-user postgres "psql -d DATABASE -c '\dx' | grep citus"

## Upgrade PostgreSQL
### Prepare for the PostgreSQL upgrade

#### 1. Update `public.yml`

public.yml:
```yaml
citus_postgresql_version: NEW-VERSION
citus_postgresql_port: NEW-PORT  # this must be different from the current port
```

#### 2. Run the `deploy_citusdb.yml` playbook to install the new version of PostgreSQL

    commcare-cloud <env> ansible-playbook deploy_postgres.yml --tags citusdb

### Perform the upgrade

#### 1. Stop all processes connecting to the databases

    commcare-cloud <env> run-module citusdb,!citusdb_worker service "name=pgbouncer state=stopped"

#### 2. Run the upgrade playbooks

The following commands can be used to perform the upgrade:

    commcare-cloud <env> ansible-playbook pg_upgrade_start.yml --limit citusdb \
        -e old_version=OLD-VERSION -e new_version=NEW-VERSION [-e old_port=OLD-PORT]

    commcare-cloud <env> ansible-playbook pg_upgrade_standbys.yml --limit citusdb \
        -e old_version=OLD-VERSION -e new_version=NEW-VERSION [-e old_port=OLD-PORT]

    commcare-cloud <env> ansible-playbook pg_upgrade_finalize.yml --limit citusdb \
        -e old_version=OLD-VERSION -e new_version=NEW-VERSION

Follow the instructions given in the play output.

#### 3. Revert to using the old port
Once you are satisfied with the upgrade you can revert the port change in `public.yml`
and apply the changes.

    commcare-cloud <env> ansible-playbook deploy_citusdb.yml
