# 5. Support multiple Kafka brokers

**Date:** 2018-08-16

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This version of CommCare must be deployed before rolling out this change:
[cfdabcc9](https://github.com/dimagi/commcare-hq/commit/cfdabcc9e397d21b14918fadac2087f18e8fb5f9)


## Change Context
Large scale deployments of CommCare require scaling out Kafka brokers to support the high
traffic volume (as well as for high availability). Up until now CommCare has only
supported a single broker.

## Details
This changes updates the CommCare settings to allow specifying multiple brokers.

## Steps to update
Ensure that you have deployed a version of CommCare later than the version mentioned above.
To update, run

```
commcare-cloud <env> update-config
```

This may restart services, so it is good to plan for a small blip in uptime.
