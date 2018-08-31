# System Overview

Commcare Cloud gives you the tools you need to go from an inventory of virtual machines
to a robust production setup adhering to Dimagi's own security standards and best practices.

However, in order to troubleshoot this complex system with many inter-dependencies,
you will have to have strong knowledge on your team of each of the different parts of a CommCare HQ
system and how they fit together.

This page will cover the high level system overview as well as where to look for each
component or technology to learn more.
  
{::comment}
Would be nice to get a diagram in here.
{:/comment}

## Basic Machine Configuration

This section will cover OS, system, and user-level setup
that is common among all VMs involved in a CommCare HQ production environment.

### Ubuntu Linux OS (14.04)

The system and all our tools have been well-tested on Ubuntu 14.04 Trusty Tahr
and aren't expected or guaranteed to work on any other OS or Ubuntu version.

In addition, make sure that if you have the option, to select the correct
Ubuntu build for your CPU architecture, which is almost always going to be
the **64-bit** build.
Any hardware old enough to require the 32-bit build
will also likely be unfit to host CommCare HQ.

### Users, Log-ins, and SSH

In addition to system users for each type of service,
such as `cchq` (short for "CommCare HQ"), `postgres`, `elasticsearch`, etc.
one user account will be created for each individual
to whom you will be granting access to your server machines.
This will include anyone who will be running maintenance commands or looking at logs,
and each of these users will be able to access every machine via SSH.

Dimagi has a strict policy that every individual log in using their own SSH key pair,
and that there be no other method of SSH login enabled,
and these policies are automatically implemented via the `commcare-cloud` `update-users`
command (or the `deploy-stack` command, which includes the former).

As a result or extension of these policies, it's important to keep in mind that
- Password-based log-ins are disabled for all users.
- Every individual who needs to be able to log in must have an SSH key pair,
  and their public key must be recorded in your environment's configuration files.
- There are no shared ssh credentials.
- There is no root login.
- All individuals may log in as the special `ansible` user.
  (This doesn't violate the prohibition against shared ssh credentials.)
  because each individual uses their own SSH key to do so.
- Individuals' users do not have passwords associated with them.

In addition to logging in as their own user, each individual can log in
as the special `ansible` user, because their public key will be present in that
user's `authorized_keys` file as well. This user has `sudo` privileges
as well as a password that can be used to `sudo` or become any other user via `su`.

Each individual user also has the ability to run a small number of `sudo` commands
without a password. Notably, they can run `sudo -u cchq bash`
to become the `cchq` user. This is merely a convenience,
and useful when logging in to troubleshoot. 

### Encrypted Drive

Every machine that runs a stateful service (such as a database)
will have an encrypted drive using [ecryptfs](http://ecryptfs.org/).
CommCare Cloud will configure this drive for you,
but it is important that you are aware of it, notably because it must be mounted
with its password each time the VM is rebooted before it can be used.
The mounting process is automated as well and will be run as part of the
`commcare-cloud` `after-reboot` command.

---

[︎⬅︎ Overview](..)
