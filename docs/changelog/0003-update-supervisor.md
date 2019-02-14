# 3. Update Supervisor

**Date:** 2018-07-25

**Optional per env:** _only required on some environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
Ubuntu 14.04 `apt-get install supervisor` installs supervisor 3.0b.
We occasionally have issues that could be related to supervisor,
such as processes not stopping correctly.
To rule it out as a possible cause,
we decided it was better to be on a later version of supervisor,
and one that's not in beta.

## Details
We updated our scripts to install `supervisor` via `pip` in the global env
rather than through `apt-get`, and also to remove any existing `supervisor` installed
via `apt-get`. They now install supervisor 3.3.4.

## Steps to update
To update, run

```
commcare-cloud <env> deploy-stack --tags supervisor
```

This may restart services, so it is good to plan for a small blip in uptime.
