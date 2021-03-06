<!--THIS FILE IS AUTOGENERATED: DO NOT EDIT-->
<!--See https://github.com/dimagi/commcare-cloud/blob/master/changelog/README.md for instructions-->
# 10. Restart nginx after every letsencrypt cert auto-renewal

**Date:** 2019-01-02

**Optional per env:** _only required on some environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
**Update 2019-02-26**: There was a bug in this fix and it has been superceded by
[Fix to restart nginx after every letsencrypt cert auto-renewal](0021-fix-letsencrypt-restart-nginx).

Previously you had to manually restart nginx every time letsencrypt auto-renewed,
which was about every two months.

## Details
This migration applies an update to the cron job that triggers renewing the letsencrypt cert,
that makes it also restart nginx directly after renewing.
This makes the cert renewal process completely automatic
so that staying on an up-to-date cert indefinitely
should no longer require human intervention.

## Steps to update
To apply, simply run
```
commcare-cloud <env> ansible-playbook deploy_proxy.yml
```
using the latest version of commcare-cloud.
The change was introduced in https://github.com/dimagi/commcare-cloud/pull/2532.
