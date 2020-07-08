# Deploying CommCare HQ code changes

This document will walk you through the process of updating the CommCareHQ code on your server using `commcare-cloud`.

## Prerequisites

Ensure that you have a working version of `commcare-cloud` which is configured to act on your monolith or fleet of servers. You can find more information on setting up `commcare-cloud` in the [installing `commcare-cloud`](../setup/installation.md) documentation. 

If you don't yet have a server with CommCareHQ, you can try [setting up a monolith](../setup/new_environment.md). 

All commands listed here will be run from your control machine which has `commcare-cloud` installed.

## Step 1: Update `commcare-cloud`

We first want to pull the latest code for `commcare-cloud` to make sure it has the latest bugfixes by running:

``` bash
$ update-code
```

This command will update the `commcare-cloud` command from GitHub and apply any updates required. You can see exactly what this command does in [this file](https://github.com/dimagi/commcare-cloud/blob/master/control/update_code.sh).

## Step 2: Deploy new CommCareHQ code to all machines

CommCareHQ is deployed using [`fabric`](http://www.fabfile.org/), which ensures only the necessary code is deployed to each machine.

Envoke the `deploy` command by running:

``` bash
$ commcare-cloud <env> deploy
```
where you will substitute `<env>` for the name of the environment you wish to deploy to.

### Preindex Command

The first step in deploy is what we call a `preindex`, which updates any CouchDB views and Elasticsearch indices. This only runs when changes need to be made, and may take a while depending on the volume of data that you have in these data stores. You may need to wait for this process to complete in order to complete deploy. 

If your server has email capabilities, you can look out for an email notification with the subject: `[<env>_preindex] HQAdmin preindex_everything may or may not be complete`. This will be sent to the `SERVER_EMAIL` email address defined in the Django settings file.

You can also try running:

``` bash
$ commcare-cloud <env> django-manage preindex_everything --check
```

If this command exits with no output, there is still a preindex ongoing. 

## Step 3: Checking services once deploy is complete

Once deploy has completed successfully, the script will automatically restart each service, as required. You can check that the system is in a good state by running:

``` bash
$ commcare-cloud <env> django-manage check_services
```

This will provide a list of all services which are running in an unexpected state.

You may also wish to monitor the following pages, which provide similar information if you are logged in to CommCareHQ as a superuser:

  * `https://<commcare url>/hq/admin/system/`
  * `https://<commcare url>/hq/admin/system/check_services`

# Advanced

The following commands may be useful in certain circumstances.

## Run a pre-index
When there are changes that require a reindex of some database indexes it is possible to do that indexing prior to the deploy so that the deploy goes more smoothly.

Examples of change that woud result in a reindex are changes to a CouchDB view, or changes to an Elasticsearch index.

To perform a pre-index:

``` bash
$ commcare-cloud <env> fab preindex_views
```

## Resume failed deploy
If something goes wrong and the deploy fails part way through you may be able to resume it as follows:

``` bash
$ commcare-cloud <env> deploy --resume
```

## Roll back a failed deploy

You may also wish to revert to a previous version of the CommCareHQ code if the version you just deployed was not working for some reason. Before reverting, you should ensure that there were no database migrations that were run during the previous deploy that would break if you revert to a previous version.

``` bash
$ commcare-cloud <env> fab rollback
```

## Deploy static settings files

When changes are made to the static configuration files (like `localsettings.py`), you will need to deploy those static changes independently. 

``` bash
$ cchq <env> update-config
```

# Deploying Formplayer

In addition to the regular deploy, you must also separately deploy the service that backs Web Apps and App Preview, called formplayer. Since it is updated less frequently, we recommend deploying formplayer changes less frequently as well. Doing so causes about 1 minute of service interruption to Web Apps and App Preview, but keeps these services up to date.

``` bash
commcare-cloud <env> deploy formplayer
```

## Formplayer static settings

Some Formplayer updates will require deploying the application settings files. You can limit the local settings deploy to only Formplayer machines to roll these out

``` bash
$ cchq <env> update-config --limit formplayer
```

# Scheduling Deploys

## CommCare deploy

Internally at Dimagi the main cloud environment is deployed **every weekday**. 

However, for locally hosted deployments, we recommend deploying **once a week** (for example, every Wednesday), to keep up to date with new features and security patches.

Since CommCareHQ is an Open Source project, you can see all the new features that were recently merged by looking at the [merged pull requests](https://github.com/dimagi/commcare-hq/pulls?q=is%3Apr+is%3Aclosed "merged pull requests") on GitHub.

## Formplayer deploy

In addition to the regular deploy, we recommend deploying formplayer **once a month**.

## Local Settings deploy

Settings generally only need to be deployed when static files are updated against your specific environment. 

Sometimes changes are made to the system which require new settings to be deployed before code can be rolled out. In these cases, the detailed steps are provided in the [changelog](../changelog/index.md). To be notified of these changes, the [Developer Forum](https://forum.dimagi.com/) has a [dedicated topic](https://forum.dimagi.com/c/developers/maintainer-announcements/) which you can subscribe to.
