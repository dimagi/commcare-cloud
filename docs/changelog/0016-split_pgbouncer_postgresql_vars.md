# 16. Split pgbouncer vars from postgresql vars

**Date:** 2019-02-26

**Optional per env:** _only required on some environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
This change extracts a new role from the existing postgresql role for installing
and configuring pgbouncer.

As a result of this change the `postgresql.yml` environment configuration file
needs to be changed to split out the postgresql vars from the pgbouncer vars.

## Details
Previously there was a field in `<env>/postgresql.yml` called `override` which allowed
overriding vars from the postgresql role. This var has now been split in two to represent
the two distinct roles for postgresql and pgbouncer.

The vars should be split accordingly.

## Steps to update
Edit the `postgresql.yml` file in all environments to split the `override` var as follows:

```diff
- override:
+ pgbouncer_override:
    pgbouncer_pool_mode: transaction
    pgbouncer_*
+
+ postgres_override:
    postgresql_version: "9.6"
    postgresql_*
```
