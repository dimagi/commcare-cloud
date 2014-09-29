# Ansible deployment orchestration and configuration management

This repository represents a workable role for deploying a single new
"webworker" to a given stack for the commcare-hq application.

To test the role, a vagrant file has been added that will provide the required
servers for a multi-machine deployment similar to the US production stack
described in
[Dimagi devops needs](https://docs.google.com/document/d/1tQFDC56SU8N1M-1abDWpnQKti2zYroTPBC2EmeIM8SA/pub)

Simply start the vagrant cluster and then ssh into the control box to run an
ansible deployment:

```
$ vagrant up
...
$ vagrant ssh control
...
$ cd /vagrant/commcare-ansible-master
$ ansible-playbook -i inventories/development deploy_stack.yml -e "deploy_env=dev version=HEAD"
```

This will build a database server, a proxy server and a single web worker,
hooked into both appropriately.

Once the preliminary deployment is complete, a new web worker may be added
simply by editing the file `inventories/development.yml` and adding the second
web worker server IP address:

```ini
[webworkers]
192.168.33.15
192.168.33.18
```
