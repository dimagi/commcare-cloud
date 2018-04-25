# Running Commands with `commcare-cloud`

All commcare-cloud commands take the following form:

```
commcare-cloud <env> <command> <args...>
```

Additionally, `commcare-cloud` is aliased to the easier-to-type `cchq`
(short for "CommCare HQ"), so any command you see here can also be run
as

```
cchq <env> <command> <args...>
```

## Available commands

### Internal Housekeeping for your `commcare-cloud` environments


#### `commcare-cloud <env> validate-environment-settings`

_Validate your environment's configuration files_

As you make changes to your environment files, you can use this
command to check for validation errors or incompatibilities.

#### `commcare-cloud <env> update-local-known-hosts`

_Update the local known_hosts file of the environment configuration._

You can run this on a regualar basis to avoid having to `yes` through
the ssh prompts. Note that when you run this, you are implicitly
trusting that at the moment you run it, there is no man-in-the-middle
attack going on, the type of security breech that the SSH prompt
is meant to mitigate against in the first place.

### Ad-hoc

#### `commcare-cloud <env> lookup <server>`

_Lookup remote hostname or IP address_

`<server>`: Server name/group: postgresql, proxy, webworkers, ... The server
name/group may be prefixed with 'username@' to login as a
specific user and may be terminated with ':<n>' to choose one of
multiple servers if there is more than one in the group. For
example: webworkers:0 will pick the first webworker. May also be
omitted for environments with only a single server.

#### `commcare-cloud <env> ssh <server> <ssh args...>`

_Connect to a remote host with ssh_

This will also automatically add the ssh argument `-A`
when `<server>` is `control`.

#### `commcare-cloud <env> mosh <server> <mosh args...>`

_Connect to a remote host with mosh_

This will also automatically switch to using ssh with `-A`
when `<server>` is `control` (because `mosh` doesn't support `-A`).


#### `commcare-cloud <env> run-shell-command <inventory_group> <shell_command>`

_Run an arbitrary command via the Ansible shell module._

The command is run on `<inventory_group>`. Example:

```
commcare-cloud <env> run-shell-command all 'df -h | grep /opt/data'
```

(to get disk usage stats for `/opt/data` on every machine.)


#### `commcare-cloud <env> run-module <inventory_group> <module> <module_args>`

_Run an arbitrary Ansible module._

For example,
```
commcare-cloud <env> run-module all debug "msg={{ inventory_hostname }}"
```

To print out the `inventory_hostname` ansible variable for each machine.

#### `commcare-cloud <env> django-manage [--tmux] [--release <release>] <command> <args...>`

_Run a django management command.
`commcare-cloud <env> django-manage ...` runs `./manage.py ...`
on the first webworker of <env>. Omit <command> to see a full list
of possible commands._

`[--tmux]`: if this option is included, the management command will be
run in a new tmux window under the `cchq` user. You may then exit using
the customary tmux command `^b` `d`, and resume the session later.
This is especially useful for long-running commands.

`[--release <release>]`: Name of release to run under.
E.g. '2018-04-13_18.16'.
If none is specified, the `current` release will be used.

#### `commcare-cloud <env> tmux <server> [<remote_command>]`

_Connect to a remote host with ssh and open a tmux session_

`<server>`: server to run tmux session on.
Use '-' to for default (webworkers:0)

`[<remote_command>]`: command to run in the tmux.
If a command specified, then it will always run in a new window.
If a command is *not* specified, then a it will rejoin the most
recently visited tmux window; only if there are no currently open
tmux windows will a new one be opened.

### Operational

#### `ansible-playbook` (`ap`)


_Run a playbook as you would with ansible-playbook,
but with boilerplate settings already set based on your <environment>.
By default, you will see --check output and then asked whether to apply._

#### `deploy-stack` (`aps`)

_Run the ansible playbook for deploying the entire stack.
Often used in conjunction with --limit and/or --tag
for a more specific update._

#### `update-config`

_Run the ansible playbook for updating app config such as
django localsettings.py and formplayer application.properties._

#### `after-reboot`

_Bring a just-rebooted machine back into operation.
Includes mounting the encrypted drive._

#### `restart-elasticsearch`

_Do a rolling restart of elasticsearch._

#### `bootstrap-users`

_Add users to a set of new machines as root.
This must be done before any other user can log in._

#### `update-users`

_Add users to a set of new machines as root.
This must be done before any other user can log in._

#### `update-supervisor-confs`


_Updates the supervisor configuration files
for services required by CommCare.
These services are defined in app-processes.yml._

#### `fab`

_Run a fab command as you would with fab_

#### `service`

_Manage services._

#### `migrate_couchdb`

_Perform a CouchDB migration_

#### `downtime`

_Manage downtime for the selected environment._


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
