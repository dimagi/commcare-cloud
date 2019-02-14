# 2. Update supervisor service definitions

**Date:** 2018-07-13

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
There are several CommCare specific processes that are defined in supervisor
configuration files. This change decouples the process definitions from code.

## Details
All services are now defined separately from a code deploy and outside of our
the directory where code runs.

Important Note: Any code deploys before running the following command will cause
celery and formplayer services to stop running

## Steps to update
1. Run the following to update the supervisor configuration:

```bash
commcare-cloud <env> update-supervisor-confs
```
