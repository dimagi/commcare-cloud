# Setting up a new CommCareHQ environment on a single machine

This document will walk you through the process of setting up a new monolith server to run CommCareHQ

## Prerequisites

* A single server (referred to as the "monolith" from here) with:
    * At least: 4vCPUs, 16GB RAM, 20GB drive. This is the _absolute minimum_ required to run CommCareHQ as a demo, and any production environment should be given many more resources.
    * Ubuntu 18.04 server 64-bit installed 
    * If you are using VirtualBox, you can follow the instructions on [Configuring VirtualBox for testing CommCareHQ](../howto/configure-virtualbox.md).
* Access to the monolith via SSH with a user who has sudo access. If you installed the base Ubuntu 18.04 image yourself, this should be the default.

## Step 1: Add Root User and Install Required System Packages

1. Enable root login via ssh

    On a standard Ubuntu install, the `root` user is not enabled or allowed to ssh. The root user will only be used initially, and will then be disabled automatically by the install scripts.

    Set the root password:

    ``` bash
    $ sudo passwd root
    ```

    Enable the root user

    ``` bash
    $ sudo passwd -u root
    ```

    Edit `/etc/ssh/sshd_config`:
    
    ``` bash
    $ sudo nano /etc/ssh/sshd_config
    ```
    
    and add the following line at the bottom:

    ```
    PermitRootLogin yes
    ```

    Then restart SSH:

    ``` bash
    $ service ssh reload
    ```

1. Install Required Packages

    ``` bash
    $ sudo apt install python-pip sshpass
    $ sudo pip install ansible virtualenv virtualenvwrapper --ignore-installed six
    $ sudo touch /var/log/ansible.log
    $ sudo chmod 666 /var/log/ansible.log
    ```

## Step 2: Download and configure the commcare-cloud environment

1. Clone the sample environment into the `environments` folder:

    ``` bash
    $ git clone https://github.com/dimagi/sample-environment.git environments
    ```
    
    You can read more about the files contained in this environments folder [here](../commcare-cloud/env/index.md).

1. Encrypt the provided ansible vault file by running:

    ``` bash
    $ ansible-vault encrypt ~/environments/monolith/vault.yml
    ```

    Enter a strong password when prompted, and save this password somewhere safe as you will need it for any future changes to this file, as well as when you deploy and configuration changes to this machine.
    
    More information on ansible vault can be found in the [Ansible help pages](https://docs.ansible.com/ansible/latest/user_guide/vault.html).
    
    You can read more about how we use this vault file [here](https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/ansible/README.md#managing-secrets-with-vault).

### Add passwords to the vault file

In the vault file, change each field that has the value `CHANGE ME` to a strong, unique password or a unique, useful username for that service. These usernames and passwords will be used by the `commcare-cloud` script to create the required database and system users, and no action is needed to create these users yourself.

``` bash
$ ansible-vault edit ~/environments/monolith/vault.yml
```

### Set the network interface name and ipaddress

1. Find the name and IP address of the network interface of your machine, and note it down. You can do this by running

    ``` bash
    $ ip addr
    ```
    This will give an output that looks like:

    ```
    $ ip addr
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
    ```

    Here, the network interface we are interested in is **enp0s3**, which has an IP address of `10.0.2.15`. Note these values down.

1. Open the `environments/monolith/inventory.ini` file in an editor

    ``` bash
    $ nano ~/environments/monolith/inventory.ini
    ```

    Replace the word `localhost` on the second line with the IP address you found in the previous step.

    Uncomment and set the value of `ufw_private_interface` to the network interface of your machine that we found in the previous step.


### Add a public key and user to commcare-cloud

Even though we will be running all commands locally, we still need to add the user's public key.

1. Generate a public key (optional):

    If your user already has an ssh key pair, ignore this step.

    ``` bash
    $ ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    ```

1. Add your public key to commcare-cloud by copying it to `~/environments/_authorized_keys`

    For example:
    ``` bash
    $ cp ~/.ssh/id_rsa.pub ~/environments/_authorized_keys/$(whoami).pub
    ```

1. Add your system username to the `present` section of `~/environments/_users/dimagi.yml`. This username should correspond to the name you've used for the public key in the previous step.
   
    ``` bash
    $ nano ~/environments/_users/dimagi.yml
    ```

## Step 3: Install commcare-cloud

Install commcare-cloud onto the monolith as described in [Installing commcare-cloud](installation.md#step-2) beginning with **Step 2**.

## Step 4: Set-up commcare-cloud

1. Configure `commcare-cloud`

    ``` bash
    $ COMMCARE_CLOUD_ENVIRONMENTS=/home/$(whoami)/environments manage-commcare-cloud configure

    ```
    You will see a few prompts that will guide you through the installation. Answer the questions as follows for a standard installation:
    ```
    Do you work or contract for Dimagi? [y/N]n
    ```

    ```
    I see you have COMMCARE_CLOUD_ENVIRONMENTS set to /home/{username}/environments in your environment
    Would you like to use environments at that location? [y/N]y
    ```

1. Add the commcare-cloud config to your bash profile to set the correct paths:

    ``` bash
    $ echo "source ~/.commcare-cloud/load_config.sh" >> ~/.profile
    ```
1. Load the commcare-cloud config so it takes effect immediately:

    ``` bash
    $ source ~/.commcare-cloud/load_config.sh
    ```

## Step 5: Update the known hosts file

```bash
$ commcare-cloud monolith update-local-known-hosts
```
You will be prompted for the ansible vault password that you entered in [Step 2](#step-2-download-and-configure-the-commcare-cloud-environment)

## Step 6: Install all the services onto the monolith

In this step, you will be prompted for an SSH password. This is the root user's password. After this step, the root user will not be able to log in via SSH.

``` bash
$ commcare-cloud monolith deploy-stack --first-time
```

```
This command will apply without running the check first. Continue? [y/N]y
ansible-playbook /home/{username}/commcare-cloud/src/commcare_cloud/ansible/deploy_stack.yml -i /home/{username}/environments/monolith/inventory.ini -e @/home/{username}/environments/monolith/vault.yml -e @/home/{username}/environments/monolith/public.yml -e @/home/{username}/environments/monolith/.generated.yml --diff --tags=bootstrap-users -u root --ask-pass --vault-password-file=/home/{username}/commcare-cloud/src/commcare_cloud/ansible/echo_vault_password.sh --ask-pass --ssh-common-args -o=UserKnownHostsFile=/home/{username}/environments/monolith/known_hosts
Vault Password for 'monolith': <password from encrypting vault.yml>
SSH password:<root user's password>
```
This will run a series of ansible commands that will take quite a long time to run.

If there are failures during the install, which may happen due to timing issues, you can continue running the playbook with:

``` bash
$ commcare-cloud monolith deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1'
```

## Step 7: Edit the fab config file

1. Copy the example config file:

    ``` bash
    $ cp ~/commcare-cloud/src/commcare_cloud/fab/config.example.py ~/commcare-cloud/src/commcare_cloud/fab/config.py
    ```

## Step 8: Deploy CommCare HQ

Deploying CommcareHQ for the first time needs a few things enabled first.

1. Create kafka topics:

    ``` bash
    $ commcare-cloud monolith django-manage create_kafka_topics
    ```

1. Create the CouchDB and Elasticsearch indices:

    ```
    $ commcare-cloud monolith django-manage preindex_everything
    ```

1. Run the deploy command:

    ``` bash
    $ commcare-cloud monolith fab deploy
    ```
    
    You can read more about the deploy process in the [deploy documentation](../commcare-cloud/deploy.md).

1. If deploy fails, you can restart where it left off:

    ``` bash
    $ commcare-cloud monolith fab deploy:resume=yes
    ```

## Step 9: Cleanup

CommCare Cloud will no longer need the root user to be accessible via the password. The password can be removed if you wish.

## Step 10: Running CommCareHQ

### Learning `commcare-cloud` basics

In general it will be useful to understand all the commands on the [commcare-cloud basics](../commcare-cloud/basics.md) page.

### Accessing CommCareHQ from a browser

If everything went well, you should now be able to access CommCareHQ from a browser. See the [Configuring VirtualBox for testing CommCareHQ](../howto/configure-virtualbox.md) page to find the URL which depends on your networking setup.

### Troubleshooting first time set up

If you face any issues, it is recommended to review the [Troubleshooting first time setup](./troubleshooting.md) documentation. 

### Firefighting issues once CommCareHQ is running

You may also wish to look at the [Firefighting](../firefighting/index.md) page which lists out common issues that `commcare-cloud` can resolve.

## Step 11: [Optional] Rebooting the machine

If you ever reboot this machine, make sure to follow the [after reboot procedure](../commcare-cloud/basics.md#handling-a-reboot) to bring all the services back up, and mount the encrypted drive by running: 

``` bash
$ commcare-cloud monolith after-reboot all
```

## Step 12: [Optional] Make a user

If you are following this process, we assume you have some knowledge of CommCareHQ and may already have data you want to migrate to your new cluster. By default, the monolith deploy scripts will be in `Enterprise` mode, which means there is no sign up screen. You can change this and other settings in the localsettings file, and following the [localsettings deploy instructions](../commcare-cloud/basics.md#update-commcare-hq-local-settings).

If you want to leave this setting as is, you can make a superuser with:

``` bash
$ commcare-cloud monolith django-manage make_superuser {email}
```

where `{email}` is the email address you would like to use as the username.
