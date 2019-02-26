# 17. Update supervisor confs to invoke celery directly

**Date:** 2019-02-26

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
Upgrading to celery 4.x requires removing the dependency on
django-celery, which means that the results backend provided
by django-celery has to be replaced.  This change configures
celery to use the redis results backend instead.

## Details
This change must be applied before the django-celery dependency
is removed from the commcare-hq library, otherwise celery
will not be able to store task results.

## Steps to update
Update supervisor confs:
```bash
commcare-cloud <env> update-config
```
