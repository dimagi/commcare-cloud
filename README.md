# Ansible deployment orchestration and configuration management

[![Build
Status](https://travis-ci.org/dimagi/commcarehq-ansible.svg?branch=master)](https://travis-ci.org/dimagi/commcarehq-ansible)

This repository represents a workable role for deploying a single new
"webworker" to a given stack for the commcare-hq application.

To test the role, a vagrant file has been added that will provide the required
servers for a multi-machine deployment similar to the US production stack
described in
[Dimagi devops needs](https://docs.google.com/document/d/1tQFDC56SU8N1M-1abDWpnQKti2zYroTPBC2EmeIM8SA/pub)

Begin by checkout out the source for this repostiory:

```
$ git clone https://github.com/dimagi/commcarehq-ansible
```

Then, change directories into the new clone and set up submodules:

```
$ cd commcarehq-ansible
$ git submodule init
$ git submodule update
```

Ensure you have downloaded Vagrant and virtual box
If you needed to download virtual box, you should also download a box configuration:
```
vagrant box add precise64 http://files.vagrantup.com/precise64.box
```

### Mutli-machine cluster setup

Then start vagrant:

```
$ vagrant up
```

If you run into issues starting vagrant, see the troubleshooting section at the bottom.

The `./reset-vms` command can be run at any time, possibly with a subset of the
VM names, to reset the VMs to their initial state and provision them with your
SSH key. Run `./reset-vms` without arguments for usage info.

Once this is done, you may ssh into the control server and run a full deployment:

```
$ vagrant ssh control
...
$ ansible-playbook -i inventories/development -e '@vars/dev.yml' deploy_stack.yml
```

This will build a database server, a proxy server and a single web worker,
hooked into both appropriately.

Once the preliminary deployment is complete, a new web worker may be added
simply by editing the file `ansible/inventories/development` and adding the second
web worker server IP address. Also uncomment the section of the vagrant file that refers to 'app2':

```ini
[webworkers]
192.168.33.15
192.168.33.18
```

### Monolith setup

Sometimes multi machine setup locally can be very large. In order to setup a monolith, which is just one machine, you can use this setup:
```
cp Vagrantfile-monolith Vagrantfile
vagrant up
```
The one other change needed is to point to the proper inventory. Instead of using `ansible/inventories/development`, use `ansible/inventories/monolith`:

```
$ vagrant ssh control
...
$ ansible-playbook -i inventories/monolith -e '@vars/dev.yml' deploy_stack.yml
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

### Troubleshooting

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

- Update localsettings:
  ```bash
  ansible-playbook -i inventories/development -e '@vars/dev.yml'  deploy_stack.yml --tags=localsettings
  ```
- Skip the common setup, including apt installs and updating the commcarehq code:
  ```bash
  ansible-playbook -i inventories/development -e '@vars/dev.yml'  deploy_stack.yml --skip-tags=common
  ```

Tags available:

- apache2
- aptcache
- common
- deploy
- git
- keystore
- ksplice
- localsettings
- newrelic
- slow

Note: to generate this list automatically, you can run something like

```bash
ansible-playbook -u root -i ../../commcare-hq/fab/inventory/india deploy_stack.yml -e "@../config/india/india.yml" --tags= | sed 's/ERROR: tag(s) not found in playbook: .  possible values: //g' | sed 's/,/\
/g' | xargs -I% echo - %
```


### Setting up ansible control machine

```bash
ansible-playbook -u root -i inventories/localhost deploy_control.yml -e "@../config/$ENV/$ENV.yml" --ask-sudo-pass
```

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

You must ssh in as your dev user, with SSH `ForwardAgent` enabled (see above).

```bash
git clone git@github.com:dimagi/commcarehq-ansible
. commcarehq-ansible/control/init.sh
update-code

# optional: make subsequent logins a bit more convenient
echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile
```

On subsequent logins if optional step was not done.

```bash
. init-ansible
```


### Simulate dev user setup on vagrant control machine

Add a record for your user to `dev_users.present` in `ansible/var/dev.yml`.

Login with `vagrant ssh control`

```bash
ansible-playbook -u root -i inventories/development deploy_control.yml -e @vars/dev.yml --diff
```

Login as your user: `vagrant ssh control -- -l $USER -A

```bash
ln -s /vagrant ~/commcarehq-ansible
. commcarehq-ansible/control/init.sh
echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile

# run ansible
ansible-playbook -u ansible --ask-sudo-pass -i inventories/development \
  -e @vars/dev.yml --diff deploy_stack.yml --tags=users,ssh # or whatever
```
