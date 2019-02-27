# 17. Remove celery results backend from localsettings

**Date:** 2019-02-27

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
Upgrading to celery 4.x requires removing the dependency on
django-celery, which means that its results backend will no
longer be available.  This removes the django-celery backend
as the default from localsettings, so the results backend can
be specified by commcare-hq settings instead.

## Details
If the localsettings change here is deployed prior to the
minimum CommCare version, then celery will be missing its
results backend.

If celery is upgraded to 4.x prior to applying this change,
celery will be misconfigured, using the unavailable
django-celery results backend.

## Steps to update
Update localsettings:
```bash
commcare-cloud <env> update-config
```
