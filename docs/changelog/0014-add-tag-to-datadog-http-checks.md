# 14. Add tag to datadog http checks

**Date:** 2019-02-11

**Optional per env:** Yes

## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
This change adds "check_type" tag to the http_check datadog integration.
This change applies only to envs using datadog for monitoring.

## Details
The check_type tag will allow you to set up different monitors
for "serverup" endpoint (high severity)
and "heartbeat" endpoint (usually lower severity).

## Steps to update
1. Update datadog integrations on the proxy machine:
```bash
commcare-cloud <env> deploy-stack --limit=proxy --tags=datadog_integrations
```
