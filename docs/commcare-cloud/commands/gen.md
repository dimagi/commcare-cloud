# Commands

* TOC
{:toc}

```
commcare-cloud [--control]
                      {<env>}
                      {bootstrap-users,ansible-playbook,django-manage,aps,tmux,ap,validate-environment-settings,restart-elasticsearch,deploy-stack,service,update-supervisor-confs,update-users,migrate_couchdb,lookup,run-module,update-config,mosh,after-reboot,ssh,downtime,fab,update-local-known-hosts,migrate-couchdb,run-shell-command}
                      ...
```

## Positional Arguments

### `{<env>}`
server environment to run against

## Optional Arguments

### `--control`
include to run command remotely on the control machine


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

### `validate-environment-settings`

```
commcare-cloud {<env>} validate-environment-settings
```

Validate your environment's configuration files

As you make changes to your environment files, you can use this
command to check for validation errors or incompatibilities.

### `update-local-known-hosts`

```
commcare-cloud {<env>} update-local-known-hosts
```

Update the local known_hosts file of the environment configuration.

You can run this on a regualar basis to avoid having to `yes` through
the ssh prompts. Note that when you run this, you are implicitly
trusting that at the moment you run it, there is no man-in-the-middle
attack going on, the type of security breech that the SSH prompt
is meant to mitigate against in the first place.

### `lookup`

```
commcare-cloud {<env>} lookup [server]
```

Lookup remote hostname or IP address

#### Positional Arguments

##### `server`
Server name/group: postgresql, proxy, webworkers, ... The server
name/group may be prefixed with 'username@' to login as a
specific user and may be terminated with ':<n>' to choose one of
multiple servers if there is more than one in the group. For
example: webworkers:0 will pick the first webworker. May also be
omitted for environments with only a single server.

### `ssh`

```
commcare-cloud {<env>} ssh [server]
```

Connect to a remote host with ssh.

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

```
commcare-cloud {<env>} mosh [server]
```

Connect to a remote host with mosh.

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

```
commcare-cloud {<env>} run-module [--use-pem] inventory_group module module_args
```

Run an arbitrary Ansible module.

#### Positional Arguments

##### `inventory_group`

The inventory group to run the command on. Use 'all' for all
hosts.
##### `module`
The module to run
##### `module_args`

The arguments to pass to the module

#### Optional Arguments

##### `--use-pem`
uses the pem file commcare_cloud_pem specified in public.vars

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

```
commcare-cloud {<env>} run-shell-command [--silence-warnings] [--use-pem] inventory_group shell_command
```

Run an arbitrary command via the Ansible shell module.

#### Positional Arguments

##### `inventory_group`

The inventory group to run the command on. Use 'all' for all
hosts.
##### `shell_command`

The shell command you want to run

#### Optional Arguments

##### `--silence-warnings`

Silence shell warnings (such as to use another module instead)
##### `--use-pem`
uses the pem file commcare_cloud_pem specified in public.vars

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

```
commcare-cloud {<env>} django-manage [--tmux] [--release RELEASE]
```

Run a django management command. `commcare-cloud <env> django-manage ...` runs `./manage.py ...` on the first webworker of &lt;env&gt;. Omit &lt;command&gt; to see a full list of possible commands.

#### Optional Arguments

##### `--tmux`
Run this command in a tmux and stay connected
##### `--release RELEASE`

Name of release to run under. E.g. '2018-04-13_18.16'

### `tmux`

```
commcare-cloud {<env>} tmux server [remote_command]
```

Connect to a remote host with ssh and open a tmux session

#### Positional Arguments

##### `server`
server to run tmux session on. Use '-' to for default
(webworkers:0)
##### `remote_command`

command to run in new tmux session

### `ansible-playbook`

```
commcare-cloud {<env>} ansible-playbook playbook
```

Run a playbook as you would with ansible-playbook, but with boilerplate settings already set based on your &lt;environment&gt;. By default, you will see --check output and then asked whether to apply. 

#### Positional Arguments

##### `playbook`
The ansible playbook .yml file to run.

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

```
commcare-cloud {<env>} deploy-stack
```

Run the ansible playbook for deploying the entire stack. Often used in conjunction with --limit and/or --tag for a more specific update.

### `update-config`

```
commcare-cloud {<env>} update-config
```

Run the ansible playbook for updating app config such as django localsettings.py and formplayer application.properties.

### `after-reboot`

```
commcare-cloud {<env>} after-reboot inventory_group
```

Bring a just-rebooted machine back into operation. Includes mounting the encrypted drive.

#### Positional Arguments

##### `inventory_group`

The inventory group to run the command on. Use 'all' for all
hosts.

### `restart-elasticsearch`

```
commcare-cloud {<env>} restart-elasticsearch
```

Do a rolling restart of elasticsearch.

### `bootstrap-users`

```
commcare-cloud {<env>} bootstrap-users
```

Add users to a set of new machines as root. This must be done before any other user can log in.

### `update-users`

```
commcare-cloud {<env>} update-users
```

Bring users up to date with the current CommCare Cloud settings.

### `update-supervisor-confs`

```
commcare-cloud {<env>} update-supervisor-confs
```

Updates the supervisor configuration files for services required by CommCare. These services are defined in app-processes.yml.

### `fab`

```
commcare-cloud {<env>} fab [fab_command]
```

Run a fab command as you would with fab

#### Positional Arguments

##### `fab_command`

fab command

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

```
commcare-cloud {<env>} service [--only PROCESS_PATTERN]
                                      
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

#### Positional Arguments

##### `{celery,commcare,couchdb,elasticsearch,formplayer,kafka,n
ginx,pillowtop,postgresql,rabbitmq,redis,riakcs,touchforms,webwo
rker}`

The services to run the command on
##### `{start,stop,restart,status,help}`

What action to take

#### Optional Arguments

##### `--only PROCESS_PATTERN`

Sub-service name to limit action to.
Format as 'name' or 'name:number'.
Use 'help' action to list all options.

### `migrate-couchdb`

```
commcare-cloud {<env>} migrate-couchdb migration_plan {describe,plan,migrate,commit}
```

Perform a CouchDB migration

#### Positional Arguments

##### `migration_plan`

Path to migration plan file
##### `{describe,plan,migrate,commit}`

Action to perform

### `downtime`

```
commcare-cloud {<env>} downtime [-m MESSAGE] {start,end}
```

Manage downtime for the selected environment.

#### Positional Arguments

##### `{start,end}`

#### Optional Arguments

##### `-m MESSAGE, --message MESSAGE`

Optional message to set on Datadog
