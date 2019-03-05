# 19. Remove celery results backend from localsettings

**Date:** 2019-02-27

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This version of CommCare must be deployed before rolling out this change:
[425793a8](https://github.com/dimagi/commcare-hq/commit/425793a8928910e993d3a6159ffd4a665d1fbfba)


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
