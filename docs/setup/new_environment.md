Setting up a new CommCare HQ environment
========================================

This document will walk you through the process of setting up a new
environment to run CommCare HQ. It covers both a single-server
("monolith") environment and a small cluster of virtual machines.


Requirements planning
---------------------

Start by estimating the resources that the environment will need.

### Single server

When CommCare HQ is running on a single server, this configuration is
referred to as a "monolith". A monolith will need an _absolute minimum_
of:

* 4 CPU cores
* 16 GB RAM
* 40 GB storage

These resources are only sufficient to run a demo of CommCare HQ. Any
production environment will need a lot more resources.

If you are using VirtualBox for testing CommCare HQ, you can follow the
instructions on [configuring VirtualBox](../howto/configure-virtualbox.md).

### Cluster

The following example uses a cluster of similarly resourced virtual
machines. Let us assume that we have estimated that the following will
meet the requirements of our project:

| Hostname   | vCPUs | RAM   | Storage               |
| ---------- | -----:| -----:|:--------------------- |
| control1   |     2 |  4 GB | 30 GB                 |
| proxy1     |     2 |  4 GB | 30 GB                 |
| webworker1 |     2 |  8 GB | 30 GB                 |
| webworker2 |     2 |  8 GB | 30 GB                 |
| db1        |     2 | 16 GB | 30 GB + 60 GB         |
| db2        |     2 | 16 GB | 30 GB + 60 GB + 20 GB |

db1 has an extra volume for databases. db2 has one extra volume for
databases, and another for a shared NFS volume.

### All environments

CommCare HQ environments run on Ubuntu Server 18.04 (64-bit).

During the installation of Ubuntu you will be prompted for the details
of the first user, who will have sudo access. It is convenient to name
the user "ansible". (The user can be named something else. Deploying
CommCare HQ will create an "ansible" user if one does not already
exist.)

When choosing which software to install during the Ubuntu installation,
select only "SSH Server".

You will need a domain name which directs to the monolith or the
cluster's proxy server.


Prepare all machines for automated deploy
-----------------------------------------

1. Do the following on the monolith, or on each machine in the cluster:

   1. Enable root login via SSH.

      On a standard Ubuntu install, the root user is not enabled or
      allowed to SSH. The root user will only be used initially, and
      will then be disabled automatically by the install scripts.

      Make a root password and store it somewhere safe for later
      reference.

      Set the root password:

          $ sudo passwd root

      Enable the root user:

          $ sudo passwd -u root

      Edit `/etc/ssh/sshd_config`:

          $ sudo nano /etc/ssh/sshd_config

      To allow logging in as root, set

          PermitRootLogin yes

      To allow password authentication, ensure

          PasswordAuthentication yes

      Then restart SSH:

          $ sudo service ssh reload

   2. Initialize a log file to be used in the installation process.

          $ sudo touch /var/log/ansible.log
          $ sudo chmod 666 /var/log/ansible.log

2. In the case of a monolith, there is only one machine to manage. The
   "control" machine is used for managing a cluster. In our example
   cluster, the control machine is named "control1".

   1. SSH into control1 as the "ansible" user, or the user you created
      during installation. You can skip this if you are installing a
      monolith.

      (This instruction assumes that the control machine's name resolves
      to its IP address. Replace the name with the IP address if
      necessary.)

          $ ssh ansible@control1

   2. On the control machine, or the monolith, install required
      packages:

          $ sudo apt update
          $ sudo apt install python3-pip sshpass net-tools

   3. Check your default Python version for Python 3.x

          $ python --version

   4. If your default version is not 3.x or if the "python" command was
      not found, make python3 your default by running the command below,
      otherwise skip it.

          $ sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 10

   5. Now update pip; you might encounter installation issues otherwise.

          $ sudo -H pip install --upgrade pip

   6. Lastly, install the following:

          $ sudo -H pip install ansible virtualenv virtualenvwrapper testresources --ignore-installed six


Create a user for yourself
--------------------------

In general, CommCare environments are managed by a team. Each member of
the team has their own user account.

On the control machine or the monolith, create a user for yourself, and
add them to the "sudo" user group. For example, if your username were
"jbloggs", the commands would be

    $ sudo adduser jbloggs
    ...
    $ sudo usermod -a -G sudo jbloggs


Configure SSH
-------------

If you do not have an SSH key pair already, you will need to create one.
(Substitute "jbloggs@example.com" with your email address)

    $ ssh-keygen -t rsa -b 4096 -C "jbloggs@example.com"

**Cluster only:** Copy an SSH key pair for your user to the control
machine.  For example, if the key pair you want to copy is
`~/.ssh/id_rsa` and `~/.ssh/id_rsa.pub`, then the commands to copy the
SSH key pair would be

    $ ssh-copy-id -i ~/.ssh/id_rsa.pub jbloggs@control1
    $ scp ~/.ssh/id_rsa{,.pub} control1:.ssh/

You can now log in using your SSH key:

    (jbloggs@jbloggs-pc) $ ssh control1


Install CommCare Cloud
----------------------

1. On the control machine or the monolith, install and configure Git:

        $ sudo apt install git
        $ git config --global user.name "Jay Bloggs"
        $ git config --global user.email "jbloggs@example.com"

   (Of course, substitute "Jay Bloggs" with your name, and
   "jbloggs@example.com" with your email address.)

2. Clone and initialize CommCare Cloud:

        $ git clone https://github.com/dimagi/commcare-cloud.git
        $ cd commcare-cloud
        $ source control/init.sh

   When prompted, confirm setting up the CommCare Cloud environment on
   login:

        Do you want to have the CommCare Cloud environment setup on login?
        (y/n): y

3. Clone the sample CommCare Cloud "environments" folder into your home
   directory.

        $ cd ~
        $ git clone https://github.com/dimagi/sample-environment.git environments

4. Rename your environment. You could name it after your organization or
   your project. If you are installing a monolith you could leave its
   name as "monolith". For this example we will name it "cluster".

        $ cd environments
        $ git mv monolith cluster
        $ git commit -m "Renamed environment"

5. Remove the "origin" Git remote. (You will not be pushing your changes
   back to the Dimagi "sample-environment" repository.)

        $ git remote remove origin

6. (Optional) You are encouraged to add a remote for your own Git
   repository, so that you can share and track changes to your
   environment's configuration. For example:

        $ git remote add origin git@github.com:your-organization/commcare-environment.git

7. Configure your CommCare environment.

   See
   [Configuring your CommCare Cloud Environments Directory](../commcare-cloud/env/index.md)
   for more information.


8. Add your username to the `present` section of
   `~/environments/_users/admins.yml`.

       $ nano ~/environments/_users/admins.yml

9. Copy your **public** key to `~/environments/_authorized_keys/`. The
   filename must correspond to your username.

   For example:

       $ cp ~/.ssh/id_rsa.pub ~/environments/_authorized_keys/$(whoami).pub

10. Change "monolith.commcarehq.test" to your real domain name,

        $ cd cluster

    (or whatever you named your environment, if not "cluster".)

        $ git grep -n "monolith"

    You should find references in the following files and places:

    * `proxy.yml`
      + `SITE_HOST`
    * `public.yml`
      + `ALLOWED_HOSTS`
      + `server_email`
      + `default_from_email`
      + `root_email`

11. Configure `inventory.ini`

    ### For a monolith

    1. Find the name and IP address of the network interface of your
       machine, and note it down. You can do this by running

           $ ip addr

       This will give an output that looks similar to

           1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
               link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
               inet 127.0.0.1/8 scope host lo
                  valid_lft forever preferred_lft forever
               inet6 ::1/128 scope host
                  valid_lft forever preferred_lft forever
           2: enp0s3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
               link/ether 08:00:27:48:f5:64 brd ff:ff:ff:ff:ff:ff
               inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic enp0s3
                  valid_lft 85228sec preferred_lft 85228sec
               inet6 fe80::a00:27ff:fe48:f564/64 scope link
                  valid_lft forever preferred_lft forever

       Here, the network interface we are interested in is **enp0s3**, which
       has an IP address of `10.0.2.15`. Note this address down.

    2. Open your environment's `inventory.ini` file in an editor.
       (Substitute "cluster".)

           $ nano ~/environments/cluster/inventory.ini

       Replace the word `localhost` with the IP address you found in the
       previous step.

       Uncomment and set the value of `ufw_private_interface` to the network interface of your machine.

    ### For a cluster

    Having planned and provisioned the virtual machines in your cluster, you
    will already know their hostnames and IP addresses.

    The following is an example of an `inventory.ini` file for a small
    cluster. Use it as a template for your environment's `inventory.ini`
    file:

        [proxy1]
        192.168.122.2 hostname=proxy1 ufw_private_interface=enp1s0

        [control1]
        192.168.122.3 hostname=control1 ufw_private_interface=enp1s0

        [webworker1]
        192.168.122.4 hostname=webworker1 ufw_private_interface=enp1s0

        [webworker2]
        192.168.122.5 hostname=webworker1 ufw_private_interface=enp1s0

        [db1]
        192.168.122.4 hostname=db1 ufw_private_interface=enp1s0 elasticsearch_node_name=es0 kafka_broker_id=0

        [db2]
        192.168.122.5 hostname=db1 ufw_private_interface=enp1s0 elasticsearch_node_name=es1 kafka_broker_id=1

        [control:children]
        control1

        [proxy:children]
        proxy1

        [webworkers:children]
        webworker1
        webworker2

        [celery:children]
        webworker1
        webworker2

        [pillowtop:children]
        webworker1
        webworker2

        [django_manage:children]
        webworker1

        [formplayer:children]
        webworker2

        [rabbitmq:children]
        webworker1

        [postgresql:children]
        db1
        db2

        [pg_backup:children]
        db1
        db2

        [pg_standby]

        [couchdb2:children]
        db1
        db2

        [couchdb2_proxy:children]
        db1

        [shared_dir_host:children]
        db2

        [redis:children]
        db1
        db2

        [zookeeper:children]
        db1
        db2

        [kafka:children]
        db1
        db2

        [elasticsearch:children]
        db1
        db2

12. Configure the `commcare-cloud` command.

         $ export COMMCARE_CLOUD_ENVIRONMENTS=$HOME/environments
         $ manage-commcare-cloud configure

    You will see a few prompts that will guide you through the
    installation. Answer the questions as follows for a standard
    installation. (Of course, substitute "jbloggs" with your username,
    and "cluster" with the name of your environment.)

        Do you work or contract for Dimagi? [y/N] n

        I see you have COMMCARE_CLOUD_ENVIRONMENTS set to /home/jbloggs/environments in your environment
        Would you like to use environments at that location? [y/N] y

    As prompted, add the commcare-cloud config to your profile to set
    the correct paths:

        $ echo "source ~/.commcare-cloud/load_config.sh" >> ~/.profile

    Load the commcare-cloud config so it takes effect immediately:

        $ source ~/.commcare-cloud/load_config.sh

    Copy the example fab config file:

        $ cp ~/commcare-cloud/src/commcare_cloud/config.example.py ~/commcare-cloud/src/commcare_cloud/config.py

    Update the known hosts file

        $ commcare-cloud cluster update-local-known-hosts


13. Generate secured passwords for the vault

    In this step, we'll generate passwords in the `vault.yml` file. This
    file will store all the passwords used in this CommCare environment.
    (Once again, substitute "cluster" with the name of your
    environment.)

        $ python ~/commcare-cloud/commcare-cloud-bootstrap/generate_vault_passwords.py --env='cluster'

    Before we encrypt the `vault.yml` file, have a look at the
    `vault.yml` file. (Substitute "cluster".)

        $ cat ~/environments/cluster/vault.yml

    Find the value of "ansible_sudo_pass" and record it in your password
    manager. We will need this to deploy CommCare HQ.

14. Next, we're going to set up an encrypted Ansible vault file. You'll
    need to create a strong password and save it somewhere safe. This is
    the master password that grants access to the vault. You'll need it
    for any future changes to this file, as well as when you deploy or
    make configuration changes to this machine.

    Encrypt the provided vault file, using that "ansible_sudo_pass". (As
    usual, substitute "cluster" with the name of your environment.)

        $ ansible-vault encrypt ~/environments/cluster/vault.yml

   More information on Ansible Vault can be found in
   the [Ansible help pages](https://docs.ansible.com/ansible/latest/user_guide/vault.html).

   [Managing secrets with Vault](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/README.md#managing-secrets-with-vault)
   will tell you more about how we use this vault file.


Deploy CommCare HQ services
---------------------------

**For a cluster** you will need the SSH agent to have your SSH key for
Ansible to connect to other machines.

    $ eval `ssh-agent`
    $ ssh-add ~/.ssh/id_rsa

When you run the "commcare-cloud deploy-stack", you will be prompted for
the vault password from earlier. You will also be prompted for an SSH
password. This is the root user's password. After this step, the root
user will not be able to log in via SSH.

    $ commcare-cloud cluster deploy-stack --first-time -e 'CCHQ_IS_FRESH_INSTALL=1'

    This command will apply without running the check first. Continue? [y/N]y
    ansible-playbook /home/jbloggs/commcare-cloud/src/commcare_cloud/ansible/deploy_stack.yml -i /home/jbloggs/environments/cluster/inventory.ini -e @/home/jbloggs/environments/cluster/vault.yml -e @/home/jbloggs/environments/cluster/public.yml -e @/home/jbloggs/environments/cluster/.generated.yml --diff --tags=bootstrap-users -u root --ask-pass --vault-password-file=/home/jbloggs/commcare-cloud/src/commcare_cloud/ansible/echo_vault_password.sh --ask-pass --ssh-common-args -o=UserKnownHostsFile=/home/jbloggs/environments/cluster/known_hosts
    Vault Password for 'cluster': <ansible_sudo_pass>
    SSH password: <root user's password>

This will run a series of Ansible commands that will take quite a long
time to run.

If there are failures during the install, which may happen due to timing
issues, you can continue running the playbook with:

    $ commcare-cloud cluster deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1'


Deploy CommCare HQ code
-----------------------

Deploying CommCare HQ code for the first time needs a few things set up
initially.

1. Create Kafka topics:

        $ commcare-cloud cluster django-manage create_kafka_topics

2. Create the CouchDB and Elasticsearch indices:

        $ commcare-cloud cluster django-manage preindex_everything

3. Run the "deploy" command:

        $ commcare-cloud cluster deploy

   When prompted for the `sudo` password, enter the "ansible_sudo_pass"
   value.

   See the [deploy documentation](../commcare-cloud/deploy.md) for more
   information.

   If deploy fails, you can restart where it left off:

        $ commcare-cloud cluster deploy --resume


Set up valid SSL certificates
-----------------------------

1. Run the playbook to request a Let's Encrypt certificate:

        $ commcare-cloud cluster ansible-playbook letsencrypt_cert.yml --skip-check

2. Update settings to take advantage of new certs:

        $ nano $COMMCARE_CLOUD_ENVIRONMENTS/cluster/proxy.yml

   and set `fake_ssl_cert` to `False`

3. Deploy proxy again

        $ commcare-cloud cluster ansible-playbook deploy_proxy.yml --skip-check


Clean up
--------

CommCare Cloud will no longer need the root user to be accessible via
the password. The password can be removed if you wish.


Running CommCare HQ
-------------------

### Learning `commcare-cloud` basics

In general it will be useful to understand all the commands on the
[commcare-cloud basics](../commcare-cloud/basics.md) page.


### Accessing CommCare HQ from a browser

If everything went well, you should now be able to access CommCare HQ
from a browser.

If you are using VirtualBox, see
[Configuring VirtualBox for testing CommCare HQ](../howto/configure-virtualbox.md)
to find the URL to use in your browser.


### Testing your new CommCare Environment

Run the following command to test each of the backing services as
described [here](../commcare-cloud/deploy.md#step-3-checking-services-once-deploy-is-complete).

    $ commcare-cloud cluster django-manage check_services

Following this initial setup, it is also recommended that you go through
this [new environment QA plan](./new_environment_qa.md), which will
exercise a wide variety of site functionality.


### Troubleshooting first-time setup

If you face any issues, it is recommended to review the
[Troubleshooting first time setup](./troubleshooting.md) documentation.


### Firefighting issues once CommCare HQ is running

You may also wish to look at the
[Firefighting](../firefighting/index.md) page which lists out common
issues that `commcare-cloud` can resolve.

If you ever reboot this machine, make sure to follow the
[after reboot procedure](../commcare-cloud/basics.md#handling-a-reboot)
to bring all the services back up, and mount the encrypted drive by
running:

    $ commcare-cloud cluster after-reboot all


### Ongoing maintenance

You should be familiar with [Expectations for Ongoing Maintenance](../system/maintenance-expectations.md)


Getting started with CommCare HQ
--------------------------------

### Make a user

If you are following this process, we assume you have some knowledge of
CommCare HQ and may already have data you want to migrate to your new
cluster. By default, the deploy scripts will be in `Enterprise` mode,
which means there is no sign up screen. You can change this and other
settings in the localsettings file, and following the
[localsettings deploy instructions](../commcare-cloud/basics.md#update-commcare-hq-local-settings).

If you want to leave this setting as is, you can make a superuser with:

    $ commcare-cloud cluster django-manage make_superuser {email}

where `{email}` is the email address you would like to use as the
username.


### Add a new CommCare build

In order to create new versions of applications created in the CommCare
HQ app builder, you will need to add the the latest `CommCare Mobile`
and `CommCare Core` builds to your server. You can do this by running
the command below - it will fetch the latest version from GitHub.

    $ commcare-cloud cluster django-manage add_commcare_build --latest
