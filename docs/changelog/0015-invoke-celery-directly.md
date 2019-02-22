# 15. Update supervisor confs to invoke celery directly

**Date:** 2019-02-22

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This version of CommCare must be deployed before rolling out this change:
[f67f9c81](https://github.com/dimagi/commcare-hq/commit/f67f9c8149bd71712f457c270b03b5a55077c273)


## Change Context
Upgrading to celery 4.x requires removing the dependency on
django-celery, which means that the celery management command
becomes unavailable.  This prepares for that by invoking the
celery command directly.

## Details
None
## Steps to update
Update supervisor confs:
```bash
commcare-cloud <env> update-supervisor-confs
```
