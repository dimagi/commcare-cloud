# 15. Update supervisor confs to invoke celery directly

**Date:** 2019-02-22

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This version of CommCare must be deployed before rolling out this change:
[08e5a3c1](https://github.com/dimagi/commcare-hq/commit/08e5a3c1f7482ea30f071044431e42fe1c6e2f04)


## Change Context
Upgrading to celery 4.x requires removing the dependency on
django-celery, which means that the celery management command
becomes unavailable.  This prepares for that by invoking the
celery command directly.

## Details
If the supervisor conf changes here are deployed prior to the
minimum CommCare version, then celery will be unable to start
because the file corehq/celery.py is missing.

If celery is upgraded to 4.x prior to applying these changes,
celery also will be unable to start since starting celery via
the django_celery management command is no longer possible in
celery 4.x.

## Steps to update
Update supervisor confs:
```bash
commcare-cloud <env> update-supervisor-confs
```
