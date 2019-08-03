# Setting up a Control Machine

## What is the Control Machine

The machine where `commcare-cloud` is installed is known as the control machine. It is a single machine where you will be able to run any service checks, deploy code changes and update CommCareHQ code.

If you are running a [monolith installation](./new_environment.md) this will be the same machine that you installed all the CommCareHQ services on. 

We recommend that the control machine be in the same datacenter or network as the rest of your server fleet. 

## Setting up a control machine

1. [Install `commcare-cloud`](./installation.md) on it. 
1. Configure `commcare-cloud` with [an inventory](../commcare-cloud/env/index.md#inventoryini) of your server fleet. 
1. Update the known-hosts file to access all the servers by running 
    ``` bash
    $ commcare-cloud <env> update-local-known-hosts
    ```

## User Management

User access to all machines on the fleet is managed through the control machine. User permissions are stored in the `_users` and `_authorized_keys` directories in the environment. 

See more about these files and how to update them in the [environment documentation](../commcare-cloud/env/index.md#_users).


## Accessing the control machine

Once users are correctly added, they should access the control machine with key-forwarding enabled from their own computers. From a Unix machine:

``` bash
$ ssh username@{control_machine IP} -A
```

If you are a Windows user using PuTTY to access the control machine, follow the instructions on this [SuperUser answer](https://superuser.com/a/878964) to enable key forwarding.

This will allow those users to subsequently ssh into any of the other machines in the fleet, and run any `commcare-cloud` commands directly from the control machine.

## Understanding `commcare-cloud`

Any user with access to the control machine should have a good knowledge of the [`commcare-cloud` commands ](../commcare-cloud/commands/index.md).
