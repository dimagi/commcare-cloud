# Commands

* TOC
{:toc}

## Running Commands with `commcare-cloud`

All `commcare-cloud` commands take the following form:

```
commcare-cloud [--control]
               <env>
               {bootstrap-users,ansible-playbook,django-manage,aps,tmux,ap,validate-environment-settings,restart-elasticsearch,deploy-stack,service,update-supervisor-confs,update-users,migrate_couchdb,lookup,run-module,update-config,mosh,after-reboot,ssh,downtime,fab,update-local-known-hosts,migrate-couchdb,run-shell-command}
               ...
```

## Positional Arguments

### `<env>`

server environment to run against

## Optional Arguments

### `--control`

Run command remotely on the control machine.

You can add `--control` _directly after_ `commcare-cloud` to any command
in order to run the command not from the local machine
using the local code,
but from from the control machine for that environment,
using the latest version of `commcare-cloud` available.

It works by issuing a command to ssh into the control machine,
update the code, and run the same command entered locally but with
`--control` removed. For long-running commands,
you will have to remain connected to the the control machine
for the entirety of the run.


## `cchq` alias

Additionally, `commcare-cloud` is aliased to the easier-to-type `cchq`
(short for "CommCare HQ"), so any command you see here can also be run
as

```
cchq <env> <command> <args...>
```

## Underlying tools and common arguments

The `commcare-cloud` command line tool is by and large a relatively
thin wrapper around the other tools it uses: `ansible`, `ansible-playbook`,
`ssh`, `fab`, etc. For every command you run using `commcare-cloud`,
it will print out the underlying command that it is running,
a faint blue / cyan color.
In each case, if you copy and paste the printed command directly,
it will have essentially the same affect.
(Note too that some commands run
multiple underlying commands in sequence,
and that each command will be printed.)

Where possible, `commcare-cloud` is set up to pass any unknown arguments
to the underlying tool. In addition, there are a number of common
arguments that are recognized by many `commcare-cloud` commands,
and have similar behavior on across them. Rather than include these
on every command they apply to, we will list upfront
these common arguments and when they can be used.

To verify availability on any given command, you can always run the
command with `-h`.

### Ansible-backed commands

For most ansible-backed commands `commcare-cloud`
will run in check mode first, and then ask you to confirm
before applying the changes. Since check mode does not make sense
for all commands, there are some that do not follow this pattern
and apply the changes directly.

### `--skip-check`

When this argument is included,
the "check, ask, apply" behavior described above is circumvented,
and the command is instead applied directly

### `--quiet`

Run the command without every prompting for permission to continue.
At each point, the affirmative response is assumed.

### `--branch <branch>`

In the specific case that `commcare-cloud` has been installed from
git source in egg mode (i.e. using `pip install -e .`), it will always
check that the checked-out git branch matches the `<branch>`
that is thus passed in. If this arg is not specified,
it defaults to `master`. As a consequence, when running from git branch
`master`, there is no need to use the `--branch` arg explicitly.

### `--output [actionable|minimal]`

The callback plugin to use for generating output. See
ansible-doc -t callback -l and ansible-doc -t callback.

## Available Commands

## Internal Housekeeping for your `commcare-cloud` environments


### `validate-environment-settings`

Validate your environment's configuration files

```
commcare-cloud <env> validate-environment-settings
```

As you make changes to your environment files, you can use this
command to check for validation errors or incompatibilities.


### `update-local-known-hosts`

Update the local known_hosts file of the environment configuration.

```
commcare-cloud <env> update-local-known-hosts
```

You can run this on a regualar basis to avoid having to `yes` through
the ssh prompts. Note that when you run this, you are implicitly
trusting that at the moment you run it, there is no man-in-the-middle
attack going on, the type of security breech that the SSH prompt
is meant to mitigate against in the first place.

## Ad-hoc


### `lookup`

Lookup remote hostname or IP address

```
commcare-cloud <env> lookup [server]
```

#### Positional Arguments

##### `server`

Server name/group: postgresql, proxy, webworkers, ... The server
name/group may be prefixed with 'username@' to login as a
specific user and may be terminated with ':<n>' to choose one of
multiple servers if there is more than one in the group. For
example: webworkers:0 will pick the first webworker. May also be
omitted for environments with only a single server.


### `ssh`

Connect to a remote host with ssh.

```
commcare-cloud <env> ssh [server]
```

This will also automatically add the ssh argument `-A`
when `<server>` is `control`.

All trailing arguments are passed directly to `ssh`.

#### Positional Arguments

##### `server`

Server name/group: postgresql, proxy, webworkers, ... The server
name/group may be prefixed with 'username@' to login as a
specific user and may be terminated with ':<n>' to choose one of
multiple servers if there is more than one in the group. For
example: webworkers:0 will pick the first webworker. May also be
omitted for environments with only a single server.


### `mosh`

Connect to a remote host with mosh.

```
commcare-cloud <env> mosh [server]
```

This will also automatically switch to using ssh with `-A`
when `<server>` is `control` (because `mosh` doesn't support `-A`).

All trailing arguments are passed directly to `mosh`
(or `ssh` in the edge case described above).

#### Positional Arguments

##### `server`

Server name/group: postgresql, proxy, webworkers, ... The server
name/group may be prefixed with 'username@' to login as a
specific user and may be terminated with ':<n>' to choose one of
multiple servers if there is more than one in the group. For
example: webworkers:0 will pick the first webworker. May also be
omitted for environments with only a single server.


### `run-module`

Run an arbitrary Ansible module.

```
commcare-cloud <env> run-module [--use-pem] inventory_group module module_args
```

#### Example

To print out the `inventory_hostname` ansible variable for each machine, run
```
commcare-cloud <env> run-module all debug "msg={{ '{{' }} inventory_hostname }}"
```

#### Positional Arguments

##### `inventory_group`

Machines to run on. Is anything that could be used in as a value for
`hosts` in an playbook "play", e.g.
`all` for all machines,
`webworkers` for a single group,
`celery:pillowtop` for multiple groups, etc.
See the description in [this blog](http://goinbigdata.com/understanding-ansible-patterns/)
for more detail in what can go here.

##### `module`

The name of the ansible module to run. Complete list of built-in modules
can be found at [Module Index](http://docs.ansible.com/ansible/latest/modules/modules_by_category.html).

##### `module_args`

Args for the module, formatted as a single string.
(Tip: put quotes around it, as it will likely contain spaces.)
Both `arg1=value1 arg2=value2` syntax
and `{"arg1": "value1", "arg2": "value2"}` syntax are accepted.

#### Optional Arguments

##### `--use-pem`

Rarely used argument to use pem file specified by `commcare_cloud_pem` when connecting.
Only useful on a new machine where the hosting provider gives you a pem file to connect with,
and before you've run bootstrap-users.

#### The ansible options below are available as well
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
####   Connection Options
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
####   Privilege Escalation Options
```
    control how and which user you become as on target hosts

    --become-method=BECOME_METHOD
                        privilege escalation method to use (default=sudo),
                        valid choices: [ sudo | su | pbrun | pfexec | doas |
                        dzdo | ksu | runas | pmrun ]
    -K, --ask-become-pass
                        ask for privilege escalation password
```


### `run-shell-command`

Run an arbitrary command via the Ansible shell module.

```
commcare-cloud <env> run-shell-command [--silence-warnings] [--use-pem] inventory_group shell_command
```

#### Example

```
commcare-cloud <env> run-shell-command all 'df -h | grep /opt/data'
```

to get disk usage stats for `/opt/data` on every machine.

#### Positional Arguments

##### `inventory_group`

Machines to run on. Is anything that could be used in as a value for
`hosts` in an playbook "play", e.g.
`all` for all machines,
`webworkers` for a single group,
`celery:pillowtop` for multiple groups, etc.
See the description in [this blog](http://goinbigdata.com/understanding-ansible-patterns/)
for more detail in what can go here.

##### `shell_command`

Command to run remotely.
(Tip: put quotes around it, as it will likely contain spaces.)
Cannot being with `sudo`; to do that use the ansible `--become` option.

#### Optional Arguments

##### `--silence-warnings`

Silence shell warnings (such as to use another module instead).

##### `--use-pem`

Rarely used argument to use pem file specified by `commcare_cloud_pem` when connecting.
Only useful on a new machine where the hosting provider gives you a pem file to connect with,
and before you've run bootstrap-users.

#### The ansible options below are available as well
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
####   Connection Options
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
####   Privilege Escalation Options
```
    control how and which user you become as on target hosts

    --become-method=BECOME_METHOD
                        privilege escalation method to use (default=sudo),
                        valid choices: [ sudo | su | pbrun | pfexec | doas |
                        dzdo | ksu | runas | pmrun ]
    -K, --ask-become-pass
                        ask for privilege escalation password
```


### `django-manage`

Run a django management command.

```
commcare-cloud <env> django-manage [--tmux] [--release RELEASE]
```

`commcare-cloud <env> django-manage ...`
runs `./manage.py ...` on the first webworker of &lt;env&gt;.
Omit &lt;command&gt; to see a full list of possible commands.

#### Example

To open a django shell in a tmux window using the `2018-04-13_18.16` release.

```
commcare-cloud <env> django-manage --tmux --release 2018-04-13_18.16 shell
```

#### Optional Arguments

##### `--tmux`

If this option is included, the management command will be
run in a new tmux window under the `cchq` user. You may then exit using
the customary tmux command `^b` `d`, and resume the session later.
This is especially useful for long-running commands.

##### `--release RELEASE`

Name of release to run under.
E.g. '2018-04-13_18.16'.
If none is specified, the `current` release will be used.


### `tmux`

Connect to a remote host with ssh and open a tmux session.

```
commcare-cloud <env> tmux server [remote_command]
```

#### Example

Rejoin last open tmux window.

```
commcare-cloud <env> tmux -
```

#### Positional Arguments

##### `server`

Server to run tmux session on.
Use '-' to for default (webworkers:0)

##### `remote_command`

Command to run in the tmux.
If a command specified, then it will always run in a new window.
If a command is *not* specified, then a it will rejoin the most
recently visited tmux window; only if there are no currently open
tmux windows will a new one be opened.

## Operational


### `ansible-playbook`
(Alias `ap`)

Run a playbook as you would with ansible-playbook

```
commcare-cloud <env> ansible-playbook playbook
```

By default, you will see --check output and then asked whether to apply.

#### Example

```
commcare-cloud <env> ansible-playbook deploy_proxy.yml --limit=proxy
```

#### Positional Arguments

##### `playbook`

The ansible playbook .yml file to run.
Options are the `*.yml` files located under `commcare_cloud/ansible`
which is under `src` for an egg install and under
`<virtualenv>/lib/python2.7/site-packages` for a wheel install.

#### The ansible-playbook options below are available as well
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
####   Connection Options
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
####   Privilege Escalation Options
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


### `deploy-stack`
(Alias `aps`)

Run the ansible playbook for deploying the entire stack.

```
commcare-cloud <env> deploy-stack
```

Often used in conjunction with --limit and/or --tag
for a more specific update.


### `update-config`

Run the ansible playbook for updating app config.

```
commcare-cloud <env> update-config
```

This includes django `localsettings.py` and formplayer `application.properties`.


### `after-reboot`

Bring a just-rebooted machine back into operation.

```
commcare-cloud <env> after-reboot inventory_group
```

Includes mounting the encrypted drive.
This command never runs in check mode.

#### Positional Arguments

##### `inventory_group`

Machines to run on. Is anything that could be used in as a value for
`hosts` in an playbook "play", e.g.
`all` for all machines,
`webworkers` for a single group,
`celery:pillowtop` for multiple groups, etc.
See the description in [this blog](http://goinbigdata.com/understanding-ansible-patterns/)
for more detail in what can go here.


### `restart-elasticsearch`

Do a rolling restart of elasticsearch.

```
commcare-cloud <env> restart-elasticsearch
```

**This command is deprecated.** Use

```
commcare-cloud <env> service elasticsearch restart
```

instead.


### `bootstrap-users`

Add users to a set of new machines as root.

```
commcare-cloud <env> bootstrap-users
```

This must be done before any other user can log in.

This will set up machines to reject root login and require
password-less logins based on the usernames and public keys
you have specified in your environment. This can only be run once
per machine; if after running it you would like to run it again,
you have to use `update-users` below instead.


### `update-users`

Bring users up to date with the current CommCare Cloud settings.

```
commcare-cloud <env> update-users
```

In steady state this command (and not `bootstrap-users`) should be used
to keep machine user accounts, permissions, and login information
up to date.


### `update-supervisor-confs`

Updates the supervisor configuration files for services required by CommCare.

```
commcare-cloud <env> update-supervisor-confs
```

These services are defined in app-processes.yml.


### `fab`

Run a fab command as you would with fab

```
commcare-cloud <env> fab [-l] [fab_command]
```

#### Positional Arguments

##### `fab_command`

The name of the fab task to run. It and all following arguments
will be passed on without modification to `fab`, so all normal `fab`
syntax rules apply.

#### Optional Arguments

##### `-l`

Use `-l` instead of a command to see the full list of commands.

#### Available commands
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


### `service`

Manage services.

```
commcare-cloud <env> service [--only PROCESS_PATTERN]
                             
                             {celery,commcare,couchdb,elasticsearch,formplayer,kafka,nginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webworker}
                             [{celery,commcare,couchdb,elasticsearch,formplayer,kafka,nginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webworker} ...]
                             {start,stop,restart,status,help}
```

#### Example

```
cchq <env> service postgresql status
cchq <env> service riakcs restart --only riak,riakcs
cchq <env> service celery help
cchq <env> service celery restart --limit <host>
cchq <env> service celery restart --only <queue-name>,<queue-name>:<queue_num>
cchq <env> service pillowtop restart --limit <host> --only <pillow-name>
```

Services are grouped together to form conceptual service groups.
Thus the `postgresql` service group applies to both the `postgresql`
service and the `pgbouncer` service. We'll call the actual services
"subservices" here.

#### Positional Arguments

##### `{celery,commcare,couchdb,elasticsearch,formplayer,kafka,nginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webworker}`

The name of the service group(s) to apply the action to.
There is a preset list of service groups that are supported.
More than one service may be supplied as separate arguments in a row.

##### `{start,stop,restart,status,help}`

Action can be `status`, `start`, `stop`, or `restart`.
This action is applied to every matching service.

#### Optional Arguments

##### `--only PROCESS_PATTERN`

Sub-service name to limit action to.
Format as 'name' or 'name:number'.
Use 'help' action to list all options.


### `migrate-couchdb`
(Alias `migrate_couchdb`)

Perform a CouchDB migration

```
commcare-cloud <env> migrate-couchdb migration_plan {describe,plan,migrate,commit}
```

This is a recent and advanced addition to the capabilities,
and is not yet ready for widespread use. At such a time as it is
ready, it will be more thoroughly documented.

#### Positional Arguments

##### `migration_plan`

Path to migration plan file

##### `{describe,plan,migrate,commit}`

Action to perform

- describe: Print out cluster info
- plan: generate plan details from migration plan
- migrate: stop nodes and copy shard data according to plan
- commit: update database docs with new shard allocation


### `downtime`

Manage downtime for the selected environment.

```
commcare-cloud <env> downtime [-m MESSAGE] {start,end}
```

This notifies Datadog of the planned downtime so that is is recorded
in the history, and so that during it service alerts are silenced.

#### Positional Arguments

##### `{start,end}`

#### Optional Arguments

##### `-m MESSAGE, --message MESSAGE`

Optional message to set on Datadog.
