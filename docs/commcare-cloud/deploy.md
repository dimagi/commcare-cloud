# Deploying CommCare HQ code changes

1. Update your commcare-cloud environment to make sure it's on the latest version of commcare-cloud
```
$ update-code
```
2. Connect to the VPN (if applicable)
1. Use commcare-cloud to deploy the environment

```
$ cchq <env> fab deploy

# or to run it from the control machine which usually makes it faster
$ cchq <env> --control fab deploy
```

If you had to wait for a preindex, retry deploy when the preindex completes,
which may be hours later. To check if preindex is complete...

* You can monitor email for preindex complete notification
(subject: *\[\<env>_preindex] HQAdmin preindex_everything may or may not be complete*).

* Check status at Cloudant dashboard for production (or India). You may need to be whitelisted to do so, follow Cloudant Whitelisting
* Check on production (or India) system status pages

4. Once deploy is complete check that the system is up and running:

  * https://<commcare url>/hq/admin/system/
  * https://<commcare url>/hq/admin/system/check_services

# Advanced

## Resume failed deploy
If something goes wrong and the deploy fails part way through you may
be able to resume it as follows:
```
$ commcare-cloud <env> fab deploy:"resume=yes"
```

## Deploy hot fix
In rare occasions it may be necessary to deploy a quick fix
to resolve a bug that is causing issues.

**Note:** This process
can only be used to deploy code changes and not HTML / CSS / Database
changes.

1. Create a branch from the currently deployed version
```
$ git checkout <deployed commit>
$ git checkout -b hotfix_deploy
```

2. Update branch with necessary changes and push changes to public repo
3. Deploy hotfix branch
```
$ commcare-cloud <env> fab hotfix_deploy --set code_branch=hotfix_deploy
```
