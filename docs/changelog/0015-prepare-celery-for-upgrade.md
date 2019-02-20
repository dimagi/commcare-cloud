# 15. Prepare celery for upgrade to 4.x

**Date:** 2019-02-19

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This version of CommCare must be deployed before rolling out this change:
[f67f9c81](https://github.com/dimagi/commcare-hq/commit/f67f9c8149bd71712f457c270b03b5a55077c273)


## Change Context
Upgrading to celery 4.x requires removing the dependency on
django-celery, which means that the celery management command
becomes unavailable.  This prepares for that by invoking the
celery command directly.  This also removes ```CELERY_RESULT_BACKEND```
from ```localsettings.py```, which has been moved to ```settings.py```.

## Details
This updates the celery bash scripts to run celery
without invoking a management command.

## Steps to update
1. Update localsettings:
```bash
commcare-cloud <env> update-config
```
2. Update celery bash scripts:
```bash
commcare-cloud <env> update-supervisor-confs
```
