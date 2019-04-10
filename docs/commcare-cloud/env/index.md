# Configuring your CommCare Cloud Environments Directory

A core component getting commcare-cloud to work to manage your
cluster or clusters is the environments directory.
This directory contains everything that is different about your
organization (authorized users) and cluster environments
(IP addresses, machine roles, passwords, optional settings, etc.).

You can change your environments directory by running

```
manage-commcare-cloud configure
```

or by setting the env variable `COMMCARE_CLOUD_ENVIRONMENTS`
to point to the directory.

## Going off the Dimagi example

To make things easy, the real environments dir that Dimagi uses
to manage its own environments is committed to the commcare-cloud
repo at https://github.com/dimagi/commcare-cloud/tree/master/environments.
The easiest way to create a new environment is to model it
after one of those.

## Layout of an `environments` directory

Your environments dir (traditionally named `environments`)
should look like this

- `environments`
  - `_authorized_keys`
  - `_users`
  - `<env1>`
  - `<env2>`

where `<env1>` (and `<env2>`, etc.) are is the environment's name.
Here we will describe the contents of directories prefixed with
an underscore (`_`). In the next section we will describe what goes in each environment's
directory.

### `_authorized_keys`

Each team member who will be granted access to the machines
of _any_ of the environments should have their public ssh key placed
in this directory in a file named `<username>.pub`, where `<username>`
is their username as it should appear on each machine.
These keys will be used to set up passwordless login to the machines
on each cluster they have access to.

For a guide to generating and using ssh keys, see this article on
[Generating a new SSH key and adding it to the ssh-agent](
https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/).

### `_users`

Minimally, this directory should contain one file named `<your-organization>.yml`.
If you have more than one environment, _and_ you have two environments
that require access from a different group of users, you may have one
file representing each of these groups. You may name the file anything
you wish; you will reference these files by name in the `meta.yml`
file of each environment.

Each of these files should contain YAML of the following format:

dev_users:
  present:
    - <username1>
    - <username2>
    ...
  absent:
    - <username3>
    - <username4>
    ...

To begin with, your `absent` may be empty; people rotate out of your
team, you will want to put team members who have left under `absent`.
That way, when you push your user configuration to your machines,
these users will be removed, and thus those former team members'
access will be revoked.

Each `<username>` must correspond to that used in a `<username>.pub`
under `_authorized_keys`.

## Contents of an `environment` configuration directory

As mentioned above, `commcare-cloud` supports servicing multiple
cluster environments. Each environment is given a name. For example,
at dimagi, our environments are named `production`, `staging`,
and a few others. This name is used for as the name of the directory,
given as `<env1>`, `<env2>`, etc. above.

A `commcare-cloud` environment configuration is made up of the following files:

- [`app-processes.yml`](#app-processesyml)
- [`fab-settings.yml`](#fab-settingsyml)
- [`inventory.ini`](#inventoryini)
- [`known_hosts`](#known_hosts)
- [`meta.yml`](#metayml)
- [`postgresql.yml`](#postgresqlyml)
- [`proxy.yml`](#proxyyml)
- [`public.yml`](#publicyml)
- [`vault.yml`](#vaultyml)

The purpose of each of these files and their formats will be discussed
in detail in the following sections.

### `app-processes.yml`
```
celery_processes:
  <host>:
    <queue-name>:
      pooling: [gevent|prefork]  # default prefork
      concurrency: <int>  # Required
      max_tasks_per_child: <int>
  <host>:
    ...
  ...
pillows:
  <host>:
    <ETL-processor-name>:
      num_processes: <int>
  <host>:
    ...
  ...
```

Each `<host>` must be a [host string](glossary#host-string).

Each `<queue-name>` must be one of the following values:
`async_restore_queue`, `background_queue`, `case_rule_queue`, `celery`,
`email_queue`, `export_download_queue`, `icds_dashboard_reports_queue`,
`reminder_case_update_queue`, `reminder_queue`,
`reminder_rule_queue`, `repeat_record_queue`, `saved_exports_queue`,
`sumologic_logs_queue`, `send_report_throttled`, `sms_queue`,
`submission_reprocessing_queue`, `ucr_indicator_queue`, `ucr_queue`.
For all features to work, each of these queues must
appear at least once, and up to once per host.

Under each `<queue-name>` goes the following params
- `concurrency`: Required; the concurrency configured on each worker
- `pooling`: default `prefork`; specify `prefork` or `gevent` for the
  process pool type used on each worker in this section
- `max_tasks_per_child`: default 50; only applicable for prefork pooling
  (corresponds to `maxtasksperchild` celery worker command line arg)
- num_workers: default 1; the number of workers to create
  consuming from this queue on this host

The special queue names `flower`, `beat` can appear _only_
once. These queues take no parameters (can leave as simply `{}`).

Each `<ETL-processor-name>` must be one of the following values:
`kafka-ucr-main`, `kafka-ucr-static`, `AppDbChangeFeedPillow`,
`ApplicationToElasticsearchPillow`, `CacheInvalidatePillow`,
`CaseSearchToElasticsearchPillow`, `CaseToElasticsearchPillow`,
`DefaultChangeFeedPillow`, `DomainDbKafkaPillow`,
`FormSubmissionMetadataTrackerPillow`, `GroupPillow`,
`GroupToUserPillow`, `KafkaDomainPillow`, `LedgerToElasticsearchPillow`,
`ReportCaseToElasticsearchPillow`, `ReportXFormToElasticsearchPillow`,
`SqlSMSPillow`, `UnknownUsersPillow`, `UpdateUserSyncHistoryPillow`,
`UserCacheInvalidatePillow`, `UserGroupsDbKafkaPillow`, `UserPillow`,
`XFormToElasticsearchPillow`.
For all features to work, each of these ETL processors
(called "pillows" internally to the CommCare HQ code base,
for no good reason beyond historical accident) just listed must appear
at least once, and up to once per host. An ETL processor not mentioned
will not be run at all.

See [commcare_cloud/environment/schemas/app_processes.py](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/environment/schemas/app_processes.py#L25-L40)
for complete list of top-level properties for this file.
These are subject to the defaults provided in
[commcare_cloud/environmental-defaults/app-processes.yml](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/environmental-defaults/app-processes.yml).
<!--  todo: clean up this code and then better document -->

### `fab-settings.yml`
This file contains basic settings relevent to deploying updated versions
CommCare HQ code.

### `inventory.ini`
This is the Ansible Inventory file. It lists all the hosts releveant to the
system and provides host groups for the different services. This file
can also contain host specific variables like `hostname` or configuration
for the encrypted drive.

### `known_hosts`
This file is optional and is auto-generated by running
```bash
commcare-cloud <env> update-local-known-hosts
```

For commcare-cloud commands that require opening ssh connections,
this file is used instead of `~/.ssh/known_hosts` where possible.
This allows a team to share a `known_hosts` file that is environment specific,
which has both security (depending on how used) and practical benefits
(each team member does not have to ssh into each machine
and respond `yes` to typical ssh prompt asking whether to trust a given
host based on its fingerprint).

### `meta.yml`
This file contains some global settings for the environment.

### `postgresql.yml`

This file contains configuration related to postgresql.
For more detail see [`postgresql.yml`](./postgresql_yml).

### `proxy.yml`
This file contains settings related to the Nginx proxy.

### `public.yml`
This file contains the remainder of the settings for the environement
that aren't specified in any of the aforementioned files.

### `vault.yml`
This file contains sensitive information such as database passwords.
The file is encrypted using [Ansible Vault](https://docs.ansible.com/ansible/playbooks_vault.html).
For information on managing this file see [Managing Secrets with Vault](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/README.md#managing-secrets-with-vault)
