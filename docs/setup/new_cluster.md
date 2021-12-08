Setting up a new CommCare HQ environment on a small cluster
===========================================================

This document will walk you through the process of setting up a new
cluster of virtual machines to run CommCare HQ.


Planning
--------

Start by estimating the resources that the cluster will need.

The following **example** uses a cluster of identically resourced VMs.
Each one has:

| Resource | Quantity |
| -------- | --------:|
| vCPUs    |        2 |
| RAM      | 4096 MiB |
| Storage  |   30 GiB |

We have estimated that the following VMs will meet the requirements of
our project:

* control1
* proxy1
* webworker1
* webworker2
* db1
* db2


(Example) Creating a small cluster using libvirt with KVM
---------------------------------------------------------

You can use any virtualization software stack or cloud service provider
to manage your virtual machines. As an example, here is how you might do
so using libvirt with KVM.

0. These instructions will assume that working directory is
   **/srv/virt/cchq-cluster/**. Your working directory is sure to be
   different.

1. Install the following packages on the host:

        $ sudo apt install qemu-kvm libvirt-daemon-system virtinst bridge-utils

2. Create a script named **install-vm** with the following content:

        #!/bin/sh

        if [ -z "$1" ]
        then
            echo Specify a virtual-machine name.
            exit 1
        fi

        IMAGES=/srv/virt/cchq-cluster/images

        sudo virt-install \
            --name $1 \
            --vcpus 2 \
            --ram 4096 \
            --disk path=$IMAGES/$1.img,size=30 \
            --os-type linux \
            --os-variant ubuntu18.04 \
            --location 'http://archive.ubuntu.com/ubuntu/dists/bionic/main/installer-amd64/' \
            --network network=default,model=virtio \
            --graphics none \
            --console pty,target_type=serial \
            --extra-args 'console=ttyS0,115200n8 serial'

   And make it executable:

        $ chmod +x install-vm

3. Install Ubuntu 18.04 on the VMs. For each of the machine names given
   above, run the **install-vm** script. e.g. For the "control1" VM:

        $ ./install-vm control1

   1. Set the hostname to "control1".

   2. Create a user named "ansible".

   3. When choosing software, select only "SSH Server".

   4. Once the VMs are installed, use nmap to find their IP addresses:

            $ nmap -sP 192.168.122.0/24

   5. SSH into the VM as the "ansible" user, and find the VM's network
      interface and MAC address. You will need these later.

            $ ip addr

   6. Shut the VM down:

            $ sudo halt -p

4. Configure the network for your small cluster. For this example we
   will use the default NAT, and assign static addresses to the VMs.

   1. Dump the current definition of the default network:

            $ virsh net-dumpxml --network default > network.xml

   2. Edit **network.xml**. Change the DHCP range, and set static
      addresses for the VMs. Use the MAC addresses you found in the
      previous step:

            <network>
              <name>default</name>
              ...
              <ip address='192.168.122.1' netmask='255.255.255.0'>
                <dhcp>
                  <range start='192.168.122.102' end='192.168.122.254'/>
                  <host name='proxy1.commcare.local'
                        mac='52:54:00:11:11:11'
                        ip='192.168.122.2'/>
                  <host name='control1.commcare.local'
                        mac='52:54:00:22:22:22'
                        ip='192.168.122.3'/>
                  <host name='webworker1.commcare.local'
                        mac='52:54:00:33:33:33'
                        ip='192.168.122.4'/>
                  <host name='webworker2.commcare.local'
                        mac='52:54:00:44:44:44'
                        ip='192.168.122.5'/>
                  <host name='db1.commcare.local'
                        mac='52:54:00:55:55:55'
                        ip='192.168.122.6'/>
                  <host name='db2.commcare.local'
                        mac='52:54:00:66:66:66'
                        ip='192.168.122.7'/>
                </dhcp>
              </ip>
            </network>

   3. Drop the "default" network, load the definition in
      **network.xml**, and start it up again:

            $ virsh net-destroy --network default
            $ virsh net-define --file network.xml
            $ virsh net-start --network default

   4. Start the VMs

            $ for vm in control1 proxy1 webworker1 webworker2 db1 db2
            for> do virsh start $vm
            for> done

   5. (Optional) For convenience, consider adding the hostnames and IP
      addresses of the VMs to /etc/hosts.


Prepare all VMs for automated deploy
------------------------------------

Do the following for each VM:

1. Enable root login via SSH.

   On a standard Ubuntu install, the `root` user is not enabled or
   allowed to ssh. The root user will only be used initially, and will
   then be disabled automatically by the install scripts.

   Make a root password and store it somewhere safe for later reference.

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

2. Install Required Packages

        $ sudo apt update && sudo apt install python3-pip sshpass net-tools

   Now update your pip3 version; you might encounter installation issues
   otherwise.

        $ sudo -H pip3 install --upgrade pip

   Check your default python version for python 3.x

        $ python --version

   If your default version is not 3.x or if the "python" command was not
   found, make python3 your default by running the command below,
   otherwise skip it.

        $ sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 10

   Lastly, install the following:

        $ sudo -H pip install ansible virtualenv virtualenvwrapper --ignore-installed six

3. Initialize a log file to be used in the installation process.

        $ sudo touch /var/log/ansible.log && sudo chmod 666 /var/log/ansible.log


Create your user and configure CommCare Cloud
---------------------------------------------

The "control" machine is used for managing the cluster.

1. SSH into the control1 as the "ansible" user, and create a user
   for yourself. (These instructions assume that the machines' names
   resolve to their IP addresses. Replace them with their IP addresses,
   if necessary. And, of course, if your username is not "jbloggs",
   adjust accordingly.)

        (jbloggs@host) $ ssh ansible@control1
        (ansible@control1) $ sudo adduser jbloggs
        ...
        (ansible@control1) $ sudo adduser jbloggs sudo

2. Copy an SSH key pair for your user, and log in:

        (jbloggs@host) $ ssh control1 mkdir .ssh
        (jbloggs@host) $ scp ~/.ssh/id_rsa{,.pub} control1:.ssh/
        (jbloggs@host) $ ssh control1
        (jbloggs@control1) $ cp .ssh/id_rsa.pub .ssh/authorized_keys

3. Install and configure git:

        $ sudo apt install git
        $ git config --global user.email "you@example.com"
        $ git config --global user.name "Your Name"

4. Install CommCare Cloud:

        $ git clone https://github.com/dimagi/commcare-cloud.git
        $ cd commcare-cloud
        $ source control/init.sh

   When prompted, confirm setting up the CommCare Cloud environment on
   login:

        Do you want to have the CommCare Cloud environment setup on login?
        (y/n): y

5. Clone the sample environment.

        $ cd ~
        $ git clone https://github.com/dimagi/sample-environment.git environments

6. Rename your environment. You could name it after your organization or
   your project. For this example we will name it "cluster".

        $ cd environments
        $ git mv monolith cluster
        $ git commit -m "Renamed environment"

6. Remove the "origin" git remote.

        $ git remote remove origin

7. (Optional) You are encouraged to add a remote for your own git
   repository, so that you can share and track changes to your
   environment's configuration.

        $ git remote add origin git@github.com:your-organization/commcare-environment.git

8. Configure your CommCare environment.

   See
   [Configuring your CommCare Cloud Environments Directory](../commcare-cloud/env/index.md)
   for more information.

   It is very important to add your user to `_users/admins.yml` and your
   **public** SSH key to `_authorized_keys`.

   The following is an example of **cluster/inventory.ini**:

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

        [riakcs]


9. Configure `commcare-cloud`

        $ export COMMCARE_CLOUD_ENVIRONMENTS=$HOME/environments
        $ manage-commcare-cloud configure

   You will see a few prompts that will guide you through the
   installation. Answer the questions as follows for a standard
   installation:

        Do you work or contract for Dimagi? [y/N]n

        I see you have COMMCARE_CLOUD_ENVIRONMENTS set to /home/jbloggs/environments in your environment
        Would you like to use environments at that location? [y/N]y

   As prompted, add the commcare-cloud config to your profile to set the
   correct paths:

        $ echo "source ~/.commcare-cloud/load_config.sh" >> ~/.profile

   Load the commcare-cloud config so it takes effect immediately:

        $ source ~/.commcare-cloud/load_config.sh

   Update the known hosts file

        $ commcare-cloud cluster update-local-known-hosts


10. Generate secured passwords for the vault

    In this step, we'll generate passwords in the `vault.yml` file. This
    file will store all the passwords used in this CommCare environment.

        $ python ~/commcare-cloud/commcare-cloud-bootstrap/generate_vault_passwords.py --env='cluster'

    Before we encrypt the `vault.yml` file, have a look at the `vault.yml` file.

        $ cat ~/environments/cluster/vault.yml

    Find the value of "ansible_sudo_pass" and record it in your password
    manager. We will need this to deploy CommCare HQ.

11. Next, we're going to set up an encrypted Ansible vault file. You'll
    need to create a strong password and save it somewhere safe. This is
    the master password that grants access to the vault. You'll need it
    for any future changes to this file, as well as when you deploy or
    make configuration changes to this machine.

    Encrypt the provided vault file, using that "ansible_sudo_pass":


        $ ansible-vault encrypt ~/environments/cluster/vault.yml

   More information on ansible vault can be found in
   the [Ansible help pages](https://docs.ansible.com/ansible/latest/user_guide/vault.html).

   You can read more about how we use this vault file
   [here](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/README.md#managing-secrets-with-vault).


Deploy CommCare HQ services
---------------------------

You will need the SSH agent to have your SSH key for Ansible to connect
to other machines.

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


### Testing your new CommCare Environment

Run the following command to test each of the backing services as
described [here](../commcare-cloud/deploy.md#step-3-checking-services-once-deploy-is-complete).

    $ commcare-cloud cluster django-manage check_services

Following this initial setup, it is also recommended that you go through
this [new environment QA plan](./new_environment_qa.md), which will
exercise a wide variety of site functionality.


### Troubleshooting first time set up

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
