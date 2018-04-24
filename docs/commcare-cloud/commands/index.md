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

    validate-environment-settings
                        Validate your environment's configuration files

    update-local-known-hosts
                        Update the local known_hosts file of the environment
                        configuration.

### Ad-hoc

    lookup              Lookup remote hostname or IP address
    ssh                 Connect to a remote host with ssh
    mosh                Connect to a remote host with mosh
    run-shell-command   Run an arbitrary command via the Ansible shell module.
    run-module          Run an arbitrary Ansible module.
    django-manage       Run a django management command. `commcare-cloud <env>
                        django-manage ...` runs `./manage.py ...` on the first
                        webworker of <env>. Omit <command> to see a full list
                        of possible commands.
    tmux                Connect to a remote host with ssh and open a tmux
                        session

### Operational

    ansible-playbook (ap)
                        Run a playbook as you would with ansible-playbook, but
                        with boilerplate settings already set based on your
                        <environment>. By default, you will see --check output
                        and then asked whether to apply.
    deploy-stack (aps)  Run the ansible playbook for deploying the entire
                        stack. Often used in conjunction with --limit and/or
                        --tag for a more specific update.
    update-config       Run the ansible playbook for updating app config such
                        as django localsettings.py and formplayer
                        application.properties.
    after-reboot        Bring a just-rebooted machine back into operation.
                        Includes mounting the encrypted drive.
    restart-elasticsearch
                        Do a rolling restart of elasticsearch.
    bootstrap-users     Add users to a set of new machines as root. This must
                        be done before any other user can log in.
    update-users        Add users to a set of new machines as root. This must
                        be done before any other user can log in.
    update-supervisor-confs
                        Updates the supervisor configuration files for
                        services required by CommCare. These services are
                        defined in app-processes.yml.
    fab                 Run a fab command as you would with fab
    service             Manage services.
    migrate_couchdb     Perform a CouchDB migration
    downtime            Manage downtime for the selected environment.


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
