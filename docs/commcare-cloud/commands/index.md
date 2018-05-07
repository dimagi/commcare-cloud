# Commands

* TOC
{:toc}

## Running Commands with `commcare-cloud`

All `commcare-cloud` commands take the following form:

```
commcare-cloud <env> <command> <args...>
```

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
commcare-cloud <env> lookup <server>
```

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
commcare-cloud <env> ssh <server> <ssh args...>
```

This will also automatically add the ssh argument `-A`
when `<server>` is `control`.

All trailing arguments are passed directly to `ssh`.

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
commcare-cloud <env> mosh <server> <mosh args...>
```

This will also automatically switch to using ssh with `-A`
when `<server>` is `control` (because `mosh` doesn't support `-A`).

All trailing arguments are passed directly to `mosh`
(or `ssh` in the edge case described above).

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
commcare-cloud <env> run-module <inventory_group> <module> <module_args> [--use-pem]
```

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
Both `'arg1=value1 arg2=value2` syntax
and `{"arg1": "value1", "arg2": "value2"}` syntax are accepted.

##### `[--use-pem]`

Rarely used argument to use pem file specified by `commcare_cloud_pem` when connecting.
Only useful on a new machine where the hosting provider gives you a pem file to connect with,
and before you've run bootstrap-users.

##### Example

To print out the `inventory_hostname` ansible variable for each machine.
```
commcare-cloud <env> run-module all debug "msg={{ inventory_hostname }}"
```

### `run-shell-command`

Run an arbitrary command via the Ansible shell module.

```
commcare-cloud <env> run-shell-command <inventory_group> <shell_command> [--silence-warnings]
```

##### `inventory_group`

See [`run-module`](#run-module).

##### `shell_command`

Command to run remotely.
(Tip: put quotes around it, as it will likely contain spaces.)
Cannot being with `sudo`; to do that use the ansible `--become` option.

##### `[--silence-warnings]`

Silence shell warnings (such as to use another module instead).

##### Example
```
commcare-cloud <env> run-shell-command all 'df -h | grep /opt/data'
```

(to get disk usage stats for `/opt/data` on every machine.)

### `django-manage`

Run a django management command.
`commcare-cloud <env> django-manage ...` runs `./manage.py ...`
on the first webworker of <env>. Omit <command> to see a full list
of possible commands.

```
commcare-cloud <env> django-manage [--tmux] [--release <release>] <command> <args...>
```

##### `[--tmux]`

If this option is included, the management command will be
run in a new tmux window under the `cchq` user. You may then exit using
the customary tmux command `^b` `d`, and resume the session later.
This is especially useful for long-running commands.

##### `[--release <release>]`

Name of release to run under.
E.g. '2018-04-13_18.16'.
If none is specified, the `current` release will be used.

##### Example

To open a django shell in a tmux window using the `2018-04-13_18.16` release.

```
commcare-cloud <env> django-manage --tmux --release 2018-04-13_18.16 shell
```

### `tmux`

Connect to a remote host with ssh and open a tmux session.

```
commcare-cloud <env> tmux <server> [<remote_command>]
```

##### `server`

Server to run tmux session on.
Use '-' to for default (webworkers:0)

##### `[<remote_command>]`

Command to run in the tmux.
If a command specified, then it will always run in a new window.
If a command is *not* specified, then a it will rejoin the most
recently visited tmux window; only if there are no currently open
tmux windows will a new one be opened.

##### Example

Rejoin last open tmux window.

```
commcare-cloud <env> tmux -
```

## Operational


### `ansible-playbook`

(Alias `ap`)

Run a playbook as you would with ansible-playbook,
but with boilerplate settings already set based on your <environment>.
By default, you will see --check output and then asked whether to apply.

```
commcare-cloud <env> ansible-playbook <playbook>
```

##### `playbook`

One of the `*.yml` files located under `commcare_cloud/ansible`
which is under `src` for an egg install and under
`<virtualenv>/lib/python2.7/site-packages` for a wheel install.

##### Example

```
commcare-cloud <env> ansible-playbook deploy_proxy.yml --limit=proxy
```

### `deploy-stack`

(Alias `aps`)

Run the ansible playbook for deploying the entire stack.
Often used in conjunction with --limit and/or --tag
for a more specific update.

```
commcare-cloud <env> deploy-stack
```

### `update-config`

Run the ansible playbook for updating app config such as
django localsettings.py and formplayer application.properties.

```
commcare-cloud <env> update-config
```


### `after-reboot`

Bring a just-rebooted machine back into operation.
Includes mounting the encrypted drive.

```
commcare-cloud <env> after-reboot
```

This command never runs in check mode.


### `restart-elasticsearch`

Do a rolling restart of elasticsearch.

This command is deprecated. Use

```
commcare-cloud <env> service elasticsearch restart
```

instead.

### `bootstrap-users`

Add users to a set of new machines as root.
This must be done before any other user can log in.

```
commcare-cloud <env> bootstrap-users
```

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

Updates the supervisor configuration files
for services required by CommCare.
These services are defined in app-processes.yml.

```
commcare-cloud <env> update-supervisor-confs
```

### `fab`

Run a fab command as you would with fab

```
commcare-cloud <env> fab [<fab_command>|-l]
```

##### `fab_command`

The name of the fab task to run. It and all following arguments
will be passed on without modification to `fab`, so all normal `fab`
syntax rules apply.

##### `-l`

Use `-l` instead of a command to see the full list of commands.

### `service`

Manage services.

Usage examples:
   cchq <env> service postgresql status
   cchq <env> service riakcs restart --only riak,riakcs
   cchq <env> service celery help
   cchq <env> service celery restart --limit <host>
   cchq <env> service celery restart --only <queue-name>,<queue-name>:<queue_num>
   cchq <env> service pillowtop restart --limit <host> --only <pillow-name>

```
comcare-cloud <env> service <services> <action:status|start|stop|restart> [--only <process_pattern>]
```

Services are grouped together to form conceptual service groups.
Thus the `postgresql` service group applies to both the `postgresql`
service and the `pgbouncer` service. We'll call the actual services
"subservices" here.

##### `services`

The name of the service group(s) to apply the action to.
There is a preset list of service groups that are supported.
More than one service may be supplied as separate arguments in a row.


##### `action`

Action can be `status`, `start`, `stop`, or `restart`.
This action is applied to every matching service.

##### `[--only <process_pattern>]`

Many service groups are made up of more than one actual service
or "subservice" as we call them here.

Here's the breakdown of service groups and the subservices they contain:

###### `supervisorctl` services

| service group | subservices |
|---------------|-------------|
| celery        | celery      |
| formplayer    | formplayer-spring |
| touchforms    | formplayer |
| webworkers    | webworkers  |

###### `service` services

| service group | subservices |
|---------------|-------------|
| couchdb2      | couchdb2    |
| es            | elasticsearch |
| kafka         | kafka, zookeeper |
| pg_standby    | postgresql, pgbouncer (just on pgstandby machines) |
| postgresql    | postgresql, pgbouncer (just on postgresql machines) |
| proxy         | nginx       |
| rabbitmq      | rabbitmq    |
| redis         | redis       |
| riakcs        | riak, riak-cs, stanchion |
| stanchion     | stanchion   |

### `migrate-couchdb`

(Deprecated alias `migrate_couchdb`)
Perform a CouchDB migration

```
commcare-cloud <env> migrate-couchdb <migration_plan> <action>
```

This is a recent and advanced addition to the capabilities,
and is not yet ready for widespread use. At such a time as it is
ready, it will be more thoroughly documented.

##### `migration_plan`

Path to migration plan file

##### `action`

Action to perform: `describe`, `plan`, `migrate`, or `commit`.


### `downtime`

Manage downtime for the selected environment.

```
commcare-cloud <env> downtime start [--message <message>]
```
or
```
commcare-cloud <env> downtime end
```

This notifies Datadog of the planned downtime so that is is recorded
in the history, and so that during it service alerts are silenced.

## The special `--control` option

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
