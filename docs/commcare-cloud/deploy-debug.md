# Resolving problems with deploys

This document outlines how to recover from issues which are enountered when performing deploys from `commcare-cloud`.

Make sure you are up to date with the documented process for [deploying to servers](deploy.md). 

All commands listed here will be run from your control machine which has `commcare-cloud` installed.

## Local Settings Mismatch

If local settings files don't match the state expected by ansible during the deploy will fail.

### Potential Causes

If `commcare-cloud` is not up to date when a deploy is run, the resulting deploy may change the local configuration of services in unintended ways, like reverting localsettings files pushed from an up-to-date deploy. If `commcare-cloud` is then updated and a new deploy occurs, the deploy can fail due to the ambiguous state.

### Example Error
Here is an example of this error which could result from

* User A updates `commcare-cloud` to add `newfile.properties` to `formplayer` and deploys that change
* User B deploys `formplayer` with an out-of-date `commcare-cloud` instance which doesn't include User A's changes
* User B updates `commcare-cloud` and attempts to deploy again


```bash
TASK [formplayer : Copy formplayer config files from current release] ***********************************************************************************************************************************************************************
failed: [10.200.9.53] (item={u'filename': u'newfile.properties'}) => {"ansible_loop_var": "item", "changed": false, "item": {"filename": "newfile.properties"}, "msg": "Source /home/cchq/www/production/formplayer_build/current/newfile.properties not found"}
```
### Resolution

After updating `commcare-cloud` and ensuring everything is up to date, running a [static settings deploy](deploy.md#deploy-static-settings-files) on the relevant machines should fix this problem, and allow the next deploy to proceed as normal.
