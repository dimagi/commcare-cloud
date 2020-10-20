# Upgrading PostgreSQL

1. Ensure that you have a full backup of all PostgreSQL data before starting the upgrade process.
2. Review the PostgreSQL documentation for the [pg_upgrade](https://www.postgresql.org/docs/current/pgupgrade.html) tool.
3. Test the upgrade process locally with Vagrant or on a test environment.

In the below instructions:

    HOSTS-TO-UPGRADE: list of hosts / host groups to upgrade include standbys
    OLD-VERSION: Current version of PostgreSQL that is running
    NEW-VERSION: Version being upgraded to
    OLD-PORT: Port that PostgreSQL is currently running on (defaults to 5432)

### Upgrade preparation

#### 1. Run the `deploy_postgres.yml` playbook to ensure your system is up to date

    commcare-cloud <env> ap deploy_postgres.yml --limit HOSTS-TO-UPGRADE

#### 2. Update PostgreSQL version and port

postgresql.yml

```yaml
postgres_override:
    postgresql_version: NEW-VERSION
    postgresql_port: NEW-PORT  # this must be different from the current PostgreSQL port
```

#### 3. Run the `deploy_postgres.yml` playbook to install the new version of PostgreSQL

    commcare-cloud <env> ap deploy_postgres.yml --limit HOSTS-TO-UPGRADE --tags postgresql

### Perform the upgrade

#### 1. Stop all processes connecting to the databases

    commcare-cloud <env> run-module HOSTS-TO-UPGRADE service "name=pgbouncer state=stopped"

#### 2. Run the upgrade playbooks

The following commands can be used to perform the upgrade:

    commcare-cloud <env> ansible-playbook pg_upgrade_start.yml --limit HOSTS-TO-UPGRADE \
        -e old_version=OLD-VERSION -e new_version=NEW-VERSION [-e old_port=OLD-PORT]

    commcare-cloud <env> ansible-playbook pg_upgrade_standbys.yml --limit HOSTS-TO-UPGRADE \
        -e old_version=OLD-VERSION -e new_version=NEW-VERSION [-e old_port=OLD-PORT]

    commcare-cloud <env> ansible-playbook pg_upgrade_finalize.yml --limit HOSTS-TO-UPGRADE \
        -e old_version=OLD-VERSION -e new_version=NEW-VERSION

Follow the instructions given in the play output.

#### 3. Revert to using the old port
Once you are satisfied with the upgrade you can revert the port change in `postgresql.yml`
and apply the changes.

    commcare-cloud <env> ansible-playbook deploy_postgres.yml --limit HOSTS-TO-UPGRADE
