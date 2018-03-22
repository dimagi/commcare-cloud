# Ansible in commcare-cloud

The roles and playbooks in this directory are intended to be used through
commcare-cloud, via commands such as `commcare-cloud <env> ansible-playbook`
and the other shortcut commands it provides.

## Todos and Deprecated things
- `ansible/vars/` still contains user keys, though these conceptually should now live
  somewhere in `environments` or `environmental_defaults`.
- There's a file `DimagiKeyStore` that we rely on (for old J2ME support)
  that isn't commited to this directory.
  Instead, to do a full deploy, one must obtain a copy of it and place it at
  ansible/roles/keystore/files/ directory.
  Originally this way because its contents are secret, it would now be preferable
  for this file to live encrypted in `environments/` or `environmental_defaults/`.

## Local vagrant setup

Ensure you have downloaded Vagrant and virtual box then start vagrant:

```
$ vagrant up
```

This will setup 4 VMs:
* 192.168.33.14 (control)
* 192.168.33.15 (app1)
* 192.168.33.16 (db1)
* 192.168.33.17 (proxy1)

See `environments/development` the configuration of this testing environment.

The VMs should be configured so that you can SSH between them as the `vagrant` user
without requiring a password.

If you run into issues starting vagrant, see the troubleshooting section at the bottom.

Once vagrant is up, you may SSH into the control server and run a full
deployment:

```
$ vagrant ssh control
...
$ commcare-cloud development deploy-stack
```

This will build a database server, a proxy server and a single web worker,
hooked into both appropriately.

Once the preliminary deployment is complete, a new web worker may be added
simply by editing the file `environments/development/inventory.ini` and adding the second
web worker server IP address. Also uncomment the section of the vagrant file that refers to 'app2':

```ini
[webworkers]
192.168.33.15
192.168.33.18
```

### Email setup

In order to have this set up send email without crashing
(which you need to do during a deploy, for example)
run a debug smtp server daemon on control:

```bash
$ vagrant ssh control
...
$ python -m smtpd -n -c DebuggingServer 0.0.0.0:1025
```

### Troubleshooting Vagrant

`vagrant up` fails.
* Start VirtualBox `$ VirtualBox`
  * Or on a Mac, `$ sudo /Library/StartupItems/VirtualBox/VirtualBox restart`
* Attempt to start the VM
  * If the error message is: `VT-x needs to be enabled in BIOS`
For the Lenovo T440s:
  * Restart machine, press Enter during startup
  * Navigate to Security -> Virtualization
    * Turn both settings on


### Running only parts of the playbook

- Only do the common setup, including apt installs and updating the commcarehq code:
  ```bash
  commcare-cloud production deploy-stack --tags=common
  ```
- Do everything _but_ the common setup:
  ```bash
  commcare-cloud production deploy-stack --skip-tags=common
  ```

### Setting up ansible control machine

This must be done as the root user.  Run `ansible-deploy-control` to get the
proper command.

### Use your ssh key to authenticate

Ansible forwards SSH requests through your local machine to authenticate with
remote servers.  This way authentication originates from your machine and your
credentials, and the ansible machine doesn't need its own auth to communicate
with other servers managed with ansible.

SSH `ForwardAgent` can be enabled by passing the `-A` flag on the command line:
```bash
$ ssh -A control.internal-va.commcarehq.org
```

You can also enable it automatically for an alias in your ssh config (note that
you then must use the alias `$ ssh control` for the settings to take effect)
```
# ~/.ssh/config
Host control
    Hostname control.internal-va.commcarehq.org
    ForwardAgent yes
```

Be careful not to enable `ForwardAgent` for untrusted hosts.

You cannot use ssh forwarding with `mosh`, so you cannot use mosh for ansible.

[troubleshooting](https://developer.github.com/guides/using-ssh-agent-forwarding/)

### Setting up a dev account on ansible control machine
See main [README](../README.md) file.

### Simulate dev user setup on vagrant control machine

Add a record for your user to `dev_users.present` in `ansible/vars/dev/dev_public.yml` and your SSH public key to
`ansible/vars/dev/users/{username}.pub`.

Login with `vagrant ssh control`

```bash
commcare-cloud development ansible-playbook deploy_control.yml -u vagrant
```

Login as your user: `vagrant ssh control -- -l $USER -A

```bash
ln -s /vagrant ~/commcare-cloud
. commcare-cloud/control/init.sh

# run ansible
ansible-playbook -u ansible --ask-sudo-pass -i inventories/development \
  -e @vars/dev/dev_private.yml -e @vars/dev/dev_public.yml \
  --diff deploy_stack.yml --tags=users,ssh # or whatever
```

#### Alternately, deploy directly from your dev environment

```bash
ansible-playbook -u vagrant -i inventories/development -e @vars/dev/dev_private.yml \
  -e @vars/dev/dev_public.yml --diff deploy_stack.yml --tags=users,ssh # or whatever
```

### Managing secrets with Vault
**IMPORTANT**: Install the git hooks to help ensure you never commit secrets into the repo: `./git-hooks/install.sh`

All the secret variables and private data required for the different environments is included
in this repository as encrypted files (`vault.yml`).

To edit these files you need to provide them on the command line when prompted (keys stored in CommCare Keepass).

To use these files with `ansible-playbook` include the `--ask-vault-pass` param.
(This is included for your convenience in the `ap` and `aps` aliases.)

#### Viewing / Editing encrypted files
You can use Vault's built in editing capability as follows:

```
ENV=production; ansible-vault edit environments/$ENV/vault.yml
```

This will decrypt the file for editing and re-encrypt it after. Note that even if no changes
are made to the file the encrypted contents will have changed.

If you just want to view the contents of the file you can use this command:

```
ENV=production; ansible-vault view environments/$ENV/vault.yml
```

#### Encrypting / Decrypting files
**CAUTION**: Make sure that you re-encrypt any files with the correct key before committing them.

The following command can be used to encrypt and decrypt files:

```
ENV=production && ansible-vault [encrypt|decrypt] filename
```

For more info on Vault see the [Ansible Documentation](https://docs.ansible.com/ansible/playbooks_vault.html)

### Running against Vagrant machines from localhost
It is also possible to run tasks on the vagrant machines from you're local machine:

```
ansible-playbook -u vagrant -i inventories/development --private-key=~/.vagrant.d/insecure_private_key -e '@vars/dev/dev_private.yml' -e '@vars/dev/dev_public.yml' deploy_stack.yml
```
