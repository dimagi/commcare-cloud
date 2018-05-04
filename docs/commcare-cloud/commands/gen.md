# `commcare-cloud`
**usage:**
```
commcare-cloud [-h] [--control]
                      {<env>}
                      {bootstrap-users,ansible-playbook,django-manage,aps,tmux,ap,update-local-known-hosts,deploy-stack,service,update-supervisor-confs,update-users,migrate_couchdb,lookup,run-module,update-config,restart-elasticsearch,mosh,after-reboot,ssh,downtime,fab,validate-environment-settings,migrate-couchdb,run-shell-command}
                      ...
```
## Positional Arguments

### `{<env>}`
server environment to run against
### `{bootstrap-users,ansible-playbook,django-manage,aps,tmux,ap,update-local-known-hosts,deploy-stack,service,update-supervisor-confs,update-users,migrate_couchdb,lookup,run-module,update-config,restart-elasticsearch,mosh,after-reboot,ssh,downtime,fab,validate-environment-settings,migrate-couchdb,run-shell-command}`

### `ansible-playbook (ap)`

Run a playbook as you would with ansible-playbook, but with boilerplate settings already set based on your <environment>. By default, you will see --check output and then asked whether to apply.
### `deploy-stack (aps)`

Run the ansible playbook for deploying the entire stack. Often used in conjunction with --limit and/or --tag for a more specific update.
### `update-config`

Run the ansible playbook for updating app config such as django localsettings.py and formplayer application.properties.
### `after-reboot`

Bring a just-rebooted machine back into operation. Includes mounting the encrypted drive.
### `restart-elasticsearch`

Do a rolling restart of elasticsearch.
### `bootstrap-users`

Add users to a set of new machines as root. This must be done before any other user can log in.
### `update-users`

Bring users up to date with the current CommCare Cloud settings.
### `update-supervisor-confs`

Updates the supervisor configuration files for services required by CommCare. These services are defined in app-processes.yml.
### `run-shell-command`

Run an arbitrary command via the Ansible shell module.
### `run-module`
Run an arbitrary Ansible module.
### `fab`
Run a fab command as you would with fab
### `lookup`
Lookup remote hostname or IP address
### `ssh`
Connect to a remote host with ssh
### `mosh`
Connect to a remote host with mosh
### `django-manage`

Run a django management command. `commcare-cloud <env> django-manage ...` runs `./manage.py ...` on the first webworker of <env>. Omit <command> to see a full list of possible commands.
### `tmux`
Connect to a remote host with ssh and open a tmux session
### `service`
Manage services.
Usage examples:   cchq <env> service postgresql status
cchq <env> service riakcs restart --only riak,riakcs
cchq <env> service celery help
cchq <env> service celery restart --limit <host>
cchq <env> service celery restart --only <queue-name>,<queue-name>:<queue_num>
cchq <env> service pillowtop restart --limit <host> --only <pillow-name>

### `validate-environment-settings`

Validate your environment's configuration files
### `update-local-known-hosts`

Update the local known_hosts file of the environment configuration.
### `migrate-couchdb (migrate_couchdb)`

Perform a CouchDB migration
### `downtime`
Manage downtime for the selected environment.

## Optional Arguments

### `-h, --help`
show this help message and exit
### `--control`
include to run command remotely on the control machine
* TOC
{:toc}
## `bootstrap-users`
**usage:**
```
commcare-cloud {<env>} bootstrap-users [-h] [--skip-check] [--quiet] [--branch BRANCH] [--output {actionable,minimal}]
                                              [-l SUBSET]
```
Add users to a set of new machines as root. This must be done before any other user can log in.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `ansible-playbook`
**usage:**
```
commcare-cloud {<env>} ansible-playbook [-h] [--skip-check] [--quiet] [--branch BRANCH]
                                               [--output {actionable,minimal}] [-l SUBSET]
                                               playbook
```
Run a playbook as you would with ansible-playbook, but with boilerplate settings already set based on your &lt;environment&gt;. By default, you will see --check output and then asked whether to apply. 

### Positional Arguments

#### `playbook`
The ansible playbook .yml file to run.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern

### The ansible-playbook options below are available as well
```
  -e EXTRA_VARS, --extra-vars=EXTRA_VARS
                        set additional variables as key=value or YAML/JSON, if
                        filename prepend with @
  --flush-cache         clear the fact cache
  --force-handlers      run handlers even if a task fails
  -f FORKS, --forks=FORKS
                        specify number of parallel processes to use
                        (default=5)
  --list-hosts          outputs a list of matching hosts; does not execute
                        anything else
  --list-tags           list all available tags
  --list-tasks          list all tasks that would be executed
  -M MODULE_PATH, --module-path=MODULE_PATH
                        prepend colon-separated path(s) to module library
                        (default=[u'/Users/droberts/.ansible/plugins/modules',
                        u'/usr/share/ansible/plugins/modules'])
  --skip-tags=SKIP_TAGS
                        only run plays and tasks whose tags do not match these
                        values
  --start-at-task=START_AT_TASK
                        start the playbook at the task matching this name
  --step                one-step-at-a-time: confirm each task before running
  --syntax-check        perform a syntax check on the playbook, but do not
                        execute it
  -t TAGS, --tags=TAGS  only run plays and tasks tagged with these values
  --vault-id=VAULT_IDS  the vault identity to use
  -v, --verbose         verbose mode (-vvv for more, -vvvv to enable
                        connection debugging)
  --version             show program's version number and exit

```
###   Connection Options
```
    control as whom and how to connect to hosts

    -k, --ask-pass      ask for connection password
    --private-key=PRIVATE_KEY_FILE, --key-file=PRIVATE_KEY_FILE
                        use this file to authenticate the connection
    -u REMOTE_USER, --user=REMOTE_USER
                        connect as this user (default=None)
    -c CONNECTION, --connection=CONNECTION
                        connection type to use (default=smart)
    -T TIMEOUT, --timeout=TIMEOUT
                        override the connection timeout in seconds
                        (default=10)
    --ssh-common-args=SSH_COMMON_ARGS
                        specify common arguments to pass to sftp/scp/ssh (e.g.
                        ProxyCommand)
    --sftp-extra-args=SFTP_EXTRA_ARGS
                        specify extra arguments to pass to sftp only (e.g. -f,
                        -l)
    --scp-extra-args=SCP_EXTRA_ARGS
                        specify extra arguments to pass to scp only (e.g. -l)
    --ssh-extra-args=SSH_EXTRA_ARGS
                        specify extra arguments to pass to ssh only (e.g. -R)

```
###   Privilege Escalation Options
```
    control how and which user you become as on target hosts

    -b, --become        run operations with become (does not imply password
                        prompting)
    --become-method=BECOME_METHOD
                        privilege escalation method to use (default=sudo),
                        valid choices: [ sudo | su | pbrun | pfexec | doas |
                        dzdo | ksu | runas | pmrun ]
    --become-user=BECOME_USER
                        run operations as this user (default=root)
    -K, --ask-become-pass
                        ask for privilege escalation password
```
## `django-manage`
**usage:**
```
commcare-cloud {<env>} django-manage [-h] [--tmux] [--release RELEASE]
```
Run a django management command. `commcare-cloud &lt;env&gt; django-manage ...` runs `./manage.py ...` on the first webworker of &lt;env&gt;. Omit &lt;command&gt; to see a full list of possible commands.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--tmux`
Run this command in a tmux and stay connected
#### `--release RELEASE`

Name of release to run under. E.g. '2018-04-13_18.16'
## `aps`
**usage:**
```
commcare-cloud {<env>} deploy-stack [-h] [--skip-check] [--quiet] [--branch BRANCH] [--output {actionable,minimal}]
                                           [-l SUBSET]
```
Run the ansible playbook for deploying the entire stack. Often used in conjunction with --limit and/or --tag for a more specific update.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `tmux`
**usage:**
```
commcare-cloud {<env>} tmux [-h] server [remote_command]
```
Connect to a remote host with ssh and open a tmux session

### Positional Arguments

#### `server`
server to run tmux session on. Use '-' to for default (webworkers:0)
#### `remote_command`

command to run in new tmux session

### Optional Arguments

#### `-h, --help`
show this help message and exit
## `ap`
**usage:**
```
commcare-cloud {<env>} ansible-playbook [-h] [--skip-check] [--quiet] [--branch BRANCH]
                                               [--output {actionable,minimal}] [-l SUBSET]
                                               playbook
```
Run a playbook as you would with ansible-playbook, but with boilerplate settings already set based on your &lt;environment&gt;. By default, you will see --check output and then asked whether to apply. 

### Positional Arguments

#### `playbook`
The ansible playbook .yml file to run.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern

### The ansible-playbook options below are available as well
```
  -e EXTRA_VARS, --extra-vars=EXTRA_VARS
                        set additional variables as key=value or YAML/JSON, if
                        filename prepend with @
  --flush-cache         clear the fact cache
  --force-handlers      run handlers even if a task fails
  -f FORKS, --forks=FORKS
                        specify number of parallel processes to use
                        (default=5)
  --list-hosts          outputs a list of matching hosts; does not execute
                        anything else
  --list-tags           list all available tags
  --list-tasks          list all tasks that would be executed
  -M MODULE_PATH, --module-path=MODULE_PATH
                        prepend colon-separated path(s) to module library
                        (default=[u'/Users/droberts/.ansible/plugins/modules',
                        u'/usr/share/ansible/plugins/modules'])
  --skip-tags=SKIP_TAGS
                        only run plays and tasks whose tags do not match these
                        values
  --start-at-task=START_AT_TASK
                        start the playbook at the task matching this name
  --step                one-step-at-a-time: confirm each task before running
  --syntax-check        perform a syntax check on the playbook, but do not
                        execute it
  -t TAGS, --tags=TAGS  only run plays and tasks tagged with these values
  --vault-id=VAULT_IDS  the vault identity to use
  -v, --verbose         verbose mode (-vvv for more, -vvvv to enable
                        connection debugging)
  --version             show program's version number and exit

```
###   Connection Options
```
    control as whom and how to connect to hosts

    -k, --ask-pass      ask for connection password
    --private-key=PRIVATE_KEY_FILE, --key-file=PRIVATE_KEY_FILE
                        use this file to authenticate the connection
    -u REMOTE_USER, --user=REMOTE_USER
                        connect as this user (default=None)
    -c CONNECTION, --connection=CONNECTION
                        connection type to use (default=smart)
    -T TIMEOUT, --timeout=TIMEOUT
                        override the connection timeout in seconds
                        (default=10)
    --ssh-common-args=SSH_COMMON_ARGS
                        specify common arguments to pass to sftp/scp/ssh (e.g.
                        ProxyCommand)
    --sftp-extra-args=SFTP_EXTRA_ARGS
                        specify extra arguments to pass to sftp only (e.g. -f,
                        -l)
    --scp-extra-args=SCP_EXTRA_ARGS
                        specify extra arguments to pass to scp only (e.g. -l)
    --ssh-extra-args=SSH_EXTRA_ARGS
                        specify extra arguments to pass to ssh only (e.g. -R)

```
###   Privilege Escalation Options
```
    control how and which user you become as on target hosts

    -b, --become        run operations with become (does not imply password
                        prompting)
    --become-method=BECOME_METHOD
                        privilege escalation method to use (default=sudo),
                        valid choices: [ sudo | su | pbrun | pfexec | doas |
                        dzdo | ksu | runas | pmrun ]
    --become-user=BECOME_USER
                        run operations as this user (default=root)
    -K, --ask-become-pass
                        ask for privilege escalation password
```
## `update-local-known-hosts`
**usage:**
```
commcare-cloud {<env>} update-local-known-hosts [-h] [--skip-check] [--quiet] [--branch BRANCH]
                                                       [--output {actionable,minimal}] [-l SUBSET]
```
Update the local known_hosts file of the environment configuration.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `deploy-stack`
**usage:**
```
commcare-cloud {<env>} deploy-stack [-h] [--skip-check] [--quiet] [--branch BRANCH] [--output {actionable,minimal}]
                                           [-l SUBSET]
```
Run the ansible playbook for deploying the entire stack. Often used in conjunction with --limit and/or --tag for a more specific update.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `service`
**usage:**
```
commcare-cloud {<env>} service [-h] [--limit LIMIT] [--only PROCESS_PATTERN]
                                      
                                      {celery,commcare,couchdb,elasticsearch,formplayer,kafka,nginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webworker}
                                      [{celery,commcare,couchdb,elasticsearch,formplayer,kafka,nginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webworker} ...]
                                      {start,stop,restart,status,help}
```
Manage services.
Usage examples:   cchq &lt;env&gt; service postgresql status
   cchq &lt;env&gt; service riakcs restart --only riak,riakcs
   cchq &lt;env&gt; service celery help
   cchq &lt;env&gt; service celery restart --limit &lt;host&gt;
   cchq &lt;env&gt; service celery restart --only &lt;queue-name&gt;,&lt;queue-name&gt;:&lt;queue_num&gt;
   cchq &lt;env&gt; service pillowtop restart --limit &lt;host&gt; --only &lt;pillow-name&gt;

### Positional Arguments

#### `{celery,commcare,couchdb,elasticsearch,formplayer,kafka,nginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webworker}`

The services to run the command on
#### `{start,stop,restart,status,help}`

What action to take

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--limit LIMIT`

Restrict the hosts to run the command on.
Use 'help' action to list all options.
#### `--only PROCESS_PATTERN`

Sub-service name to limit action to.
Format as 'name' or 'name:number'.
Use 'help' action to list all options.
## `update-supervisor-confs`
**usage:**
```
commcare-cloud {<env>} update-supervisor-confs [-h] [--skip-check] [--quiet] [--branch BRANCH]
                                                      [--output {actionable,minimal}] [-l SUBSET]
```
Updates the supervisor configuration files for services required by CommCare. These services are defined in app-processes.yml.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `update-users`
**usage:**
```
commcare-cloud {<env>} update-users [-h] [--skip-check] [--quiet] [--branch BRANCH] [--output {actionable,minimal}]
                                           [-l SUBSET]
```
Bring users up to date with the current CommCare Cloud settings.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `migrate_couchdb`
**usage:**
```
commcare-cloud {<env>} migrate-couchdb [-h] [--skip-check] migration_plan {describe,plan,migrate,commit}
```
Perform a CouchDB migration

### Positional Arguments

#### `migration_plan`

Path to migration plan file
#### `{describe,plan,migrate,commit}`

Action to perform

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
## `lookup`
**usage:**
```
commcare-cloud {<env>} lookup [-h] [server]
```
Lookup remote hostname or IP address

### Positional Arguments

#### `server`
Server name/group: postgresql, proxy, webworkers, ... The server name/group may be prefixed with 'username@' to login as a specific user and may be terminated with ':<n>' to choose one of multiple servers if there is more than one in the group. For example: webworkers:0 will pick the first webworker. May alsobe ommitted for environments with only a single server.

### Optional Arguments

#### `-h, --help`
show this help message and exit
## `run-module`
**usage:**
```
commcare-cloud {<env>} run-module [-h] [-b] [--become-user BECOME_USER] [--use-pem] [--skip-check] [--quiet]
                                         [--output {actionable,minimal}]
                                         inventory_group module module_args
```
Run an arbitrary Ansible module.

### Positional Arguments

#### `inventory_group`

The inventory group to run the command on. Use 'all' for all hosts.
#### `module`
The module to run
#### `module_args`
The arguments to pass to the module

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `-b, --become`

run operations with become (implies vault password prompting if necessary)
#### `--become-user BECOME_USER`

run operations as this user (default=root)
#### `--use-pem`
uses the pem file commcare_cloud_pem specified in public.vars
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`

### The ansible options below are available as well
```
  -B SECONDS, --background=SECONDS
                        run asynchronously, failing after X seconds
                        (default=N/A)
  -e EXTRA_VARS, --extra-vars=EXTRA_VARS
                        set additional variables as key=value or YAML/JSON, if
                        filename prepend with @
  -f FORKS, --forks=FORKS
                        specify number of parallel processes to use
                        (default=5)
  -l SUBSET, --limit=SUBSET
                        further limit selected hosts to an additional pattern
  --list-hosts          outputs a list of matching hosts; does not execute
                        anything else
  -M MODULE_PATH, --module-path=MODULE_PATH
                        prepend colon-separated path(s) to module library
                        (default=[u'/Users/droberts/.ansible/plugins/modules',
                        u'/usr/share/ansible/plugins/modules'])
  -o, --one-line        condense output
  -P POLL_INTERVAL, --poll=POLL_INTERVAL
                        set the poll interval if using -B (default=15)
  --syntax-check        perform a syntax check on the playbook, but do not
                        execute it
  -t TREE, --tree=TREE  log output to this directory
  --vault-id=VAULT_IDS  the vault identity to use
  -v, --verbose         verbose mode (-vvv for more, -vvvv to enable
                        connection debugging)
  --version             show program's version number and exit

```
###   Connection Options
```
    control as whom and how to connect to hosts

    -k, --ask-pass      ask for connection password
    --private-key=PRIVATE_KEY_FILE, --key-file=PRIVATE_KEY_FILE
                        use this file to authenticate the connection
    -u REMOTE_USER, --user=REMOTE_USER
                        connect as this user (default=None)
    -c CONNECTION, --connection=CONNECTION
                        connection type to use (default=smart)
    -T TIMEOUT, --timeout=TIMEOUT
                        override the connection timeout in seconds
                        (default=10)
    --ssh-common-args=SSH_COMMON_ARGS
                        specify common arguments to pass to sftp/scp/ssh (e.g.
                        ProxyCommand)
    --sftp-extra-args=SFTP_EXTRA_ARGS
                        specify extra arguments to pass to sftp only (e.g. -f,
                        -l)
    --scp-extra-args=SCP_EXTRA_ARGS
                        specify extra arguments to pass to scp only (e.g. -l)
    --ssh-extra-args=SSH_EXTRA_ARGS
                        specify extra arguments to pass to ssh only (e.g. -R)

```
###   Privilege Escalation Options
```
    control how and which user you become as on target hosts

    --become-method=BECOME_METHOD
                        privilege escalation method to use (default=sudo),
                        valid choices: [ sudo | su | pbrun | pfexec | doas |
                        dzdo | ksu | runas | pmrun ]
    -K, --ask-become-pass
                        ask for privilege escalation password
```
## `update-config`
**usage:**
```
commcare-cloud {<env>} update-config [-h] [--skip-check] [--quiet] [--branch BRANCH] [--output {actionable,minimal}]
                                            [-l SUBSET]
```
Run the ansible playbook for updating app config such as django localsettings.py and formplayer application.properties.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `restart-elasticsearch`
**usage:**
```
commcare-cloud {<env>} restart-elasticsearch [-h] [--skip-check] [--quiet] [--branch BRANCH]
                                                    [--output {actionable,minimal}] [-l SUBSET]
```
Do a rolling restart of elasticsearch.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `mosh`
**usage:**
```
commcare-cloud {<env>} mosh [-h] [server]
```
Connect to a remote host with mosh

### Positional Arguments

#### `server`
Server name/group: postgresql, proxy, webworkers, ... The server name/group may be prefixed with 'username@' to login as a specific user and may be terminated with ':<n>' to choose one of multiple servers if there is more than one in the group. For example: webworkers:0 will pick the first webworker. May alsobe ommitted for environments with only a single server.

### Optional Arguments

#### `-h, --help`
show this help message and exit
## `after-reboot`
**usage:**
```
commcare-cloud {<env>} after-reboot [-h] [--skip-check] [--quiet] [--branch BRANCH] [--output {actionable,minimal}]
                                           [-l SUBSET]
                                           inventory_group
```
Bring a just-rebooted machine back into operation. Includes mounting the encrypted drive.

### Positional Arguments

#### `inventory_group`

The inventory group to run the command on. Use 'all' for all hosts.

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--branch BRANCH`

the name of the commcare-cloud git branch to run against, if not master
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`
#### `-l SUBSET, --limit SUBSET`

further limit selected hosts to an additional pattern
## `ssh`
**usage:**
```
commcare-cloud {<env>} ssh [-h] [server]
```
Connect to a remote host with ssh

### Positional Arguments

#### `server`
Server name/group: postgresql, proxy, webworkers, ... The server name/group may be prefixed with 'username@' to login as a specific user and may be terminated with ':<n>' to choose one of multiple servers if there is more than one in the group. For example: webworkers:0 will pick the first webworker. May alsobe ommitted for environments with only a single server.

### Optional Arguments

#### `-h, --help`
show this help message and exit
## `downtime`
**usage:**
```
commcare-cloud {<env>} downtime [-h] [-m MESSAGE] {start,end}
```
Manage downtime for the selected environment.

### Positional Arguments

#### `{start,end}`

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `-m MESSAGE, --message MESSAGE`

Optional message to set on Datadog
## `fab`
**usage:**
```
commcare-cloud {<env>} fab [-h] [fab_command]
```
Run a fab command as you would with fab

### Positional Arguments

#### `fab_command`
fab command

### Optional Arguments

#### `-h, --help`
show this help message and exit

### Available commands
```

    apply_patch                       Used to apply a git patch created via `...
    awesome_deploy                    Preindex and deploy if it completes qui...
    check_status
    clean_offline_releases            Cleans all releases in home directory
    clean_releases                    Cleans old and failed deploys from the ...
    deploy                            Preindex and deploy if it completes qui...
    deploy_airflow
    deploy_formplayer
    development                       {{ '{{' }} hostvars[groups.proxy.0].ansible_hos...
    force_update_static
    hotfix_deploy                     deploy ONLY the code with no extra clea...
    icds                              www.icds-cas.gov.in
    icds-new                          www.icds-cas.gov.in
    kill_stale_celery_workers         Kills celery workers that failed to pro...
    manage                            run a management command
    offline_setup_release
    perform_system_checks
    pillowtop
    pna                               commcare.pna.sn
    preindex_views                    Creates a new release that runs preinde...
    prepare_offline_deploy
    production                        www.commcarehq.org
    reset_mvp_pillows
    restart_services
    reverse_patch                     Used to reverse a git patch created via...
    rollback                          Rolls back the servers to the previous ...
    rollback_formplayer
    set_supervisor_config
    setup_limited_release             Sets up a release on a single machine
    setup_release                     Sets up a full release across the clust...
    softlayer                         india.commcarehq.org
    staging                           staging.commcarehq.org
    start_celery
    start_pillows
    stop_celery
    stop_pillows
    supervisorctl
    swiss                             swiss.commcarehq.org
    unlink_current                    Unlinks the current code directory. Use...
    update_current
    update_current_supervisor_config  This only writes the supervisor config....
    webworkers
    supervisor.set_supervisor_config  Upload and link Supervisor configuratio...
```
## `validate-environment-settings`
**usage:**
```
commcare-cloud {<env>} validate-environment-settings [-h]
```
Validate your environment's configuration files

### Optional Arguments

#### `-h, --help`
show this help message and exit
## `migrate-couchdb`
**usage:**
```
commcare-cloud {<env>} migrate-couchdb [-h] [--skip-check] migration_plan {describe,plan,migrate,commit}
```
Perform a CouchDB migration

### Positional Arguments

#### `migration_plan`

Path to migration plan file
#### `{describe,plan,migrate,commit}`

Action to perform

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--skip-check`

skip the default of viewing --check output first
## `run-shell-command`
**usage:**
```
commcare-cloud {<env>} run-shell-command [-h] [--silence-warnings] [-b] [--become-user BECOME_USER] [--use-pem]
                                                [--skip-check] [--quiet] [--output {actionable,minimal}]
                                                inventory_group shell_command
```
Run an arbitrary command via the Ansible shell module.

### Positional Arguments

#### `inventory_group`

The inventory group to run the command on. Use 'all' for all hosts.
#### `shell_command`

The shell command you want to run

### Optional Arguments

#### `-h, --help`
show this help message and exit
#### `--silence-warnings`

Silence shell warnings (such as to use another module instead)
#### `-b, --become`

run operations with become (implies vault password prompting if necessary)
#### `--become-user BECOME_USER`

run operations as this user (default=root)
#### `--use-pem`
uses the pem file commcare_cloud_pem specified in public.vars
#### `--skip-check`

skip the default of viewing --check output first
#### `--quiet`
skip all user prompts and proceed as if answered in the affirmative
#### `--output {actionable,minimal}`

The callback plugin to use for generating output. See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`

### The ansible options below are available as well
```
  -B SECONDS, --background=SECONDS
                        run asynchronously, failing after X seconds
                        (default=N/A)
  -e EXTRA_VARS, --extra-vars=EXTRA_VARS
                        set additional variables as key=value or YAML/JSON, if
                        filename prepend with @
  -f FORKS, --forks=FORKS
                        specify number of parallel processes to use
                        (default=5)
  -l SUBSET, --limit=SUBSET
                        further limit selected hosts to an additional pattern
  --list-hosts          outputs a list of matching hosts; does not execute
                        anything else
  -M MODULE_PATH, --module-path=MODULE_PATH
                        prepend colon-separated path(s) to module library
                        (default=[u'/Users/droberts/.ansible/plugins/modules',
                        u'/usr/share/ansible/plugins/modules'])
  -o, --one-line        condense output
  -P POLL_INTERVAL, --poll=POLL_INTERVAL
                        set the poll interval if using -B (default=15)
  --syntax-check        perform a syntax check on the playbook, but do not
                        execute it
  -t TREE, --tree=TREE  log output to this directory
  --vault-id=VAULT_IDS  the vault identity to use
  -v, --verbose         verbose mode (-vvv for more, -vvvv to enable
                        connection debugging)
  --version             show program's version number and exit

```
###   Connection Options
```
    control as whom and how to connect to hosts

    -k, --ask-pass      ask for connection password
    --private-key=PRIVATE_KEY_FILE, --key-file=PRIVATE_KEY_FILE
                        use this file to authenticate the connection
    -u REMOTE_USER, --user=REMOTE_USER
                        connect as this user (default=None)
    -c CONNECTION, --connection=CONNECTION
                        connection type to use (default=smart)
    -T TIMEOUT, --timeout=TIMEOUT
                        override the connection timeout in seconds
                        (default=10)
    --ssh-common-args=SSH_COMMON_ARGS
                        specify common arguments to pass to sftp/scp/ssh (e.g.
                        ProxyCommand)
    --sftp-extra-args=SFTP_EXTRA_ARGS
                        specify extra arguments to pass to sftp only (e.g. -f,
                        -l)
    --scp-extra-args=SCP_EXTRA_ARGS
                        specify extra arguments to pass to scp only (e.g. -l)
    --ssh-extra-args=SSH_EXTRA_ARGS
                        specify extra arguments to pass to ssh only (e.g. -R)

```
###   Privilege Escalation Options
```
    control how and which user you become as on target hosts

    --become-method=BECOME_METHOD
                        privilege escalation method to use (default=sudo),
                        valid choices: [ sudo | su | pbrun | pfexec | doas |
                        dzdo | ksu | runas | pmrun ]
    -K, --ask-become-pass
                        ask for privilege escalation password
```
