# Setting up a new CommCareHQ environment

This document will walk you through the process of setting up a new monolith server to run CommCareHQ

## Pre-requesites

* A server with Ubuntu 18.04 installed (referred to as the "monolith" from here)
* Access to the monolith via SSH with a user who has sudo access

## Step 1: Install Required System Packages

Install pip on the monolith

``` bash
$ sudo apt install python-pip
$ sudo pip install ansible virtualenv virtualenvwrapper --ignore-installed six
```

## Step 2: Download and configure the commcare-cloud environment

1. Clone the sample environment into the `environments` folder:
 ``` bash
$ git clone https://github.com/dimagi/sample-environment.git environments
 ```

1. Encrypt the provided ansible vault file by running:

 ``` bash 
$ ansible-vault encrypt ~/environments/monolith/vault.yml
 ```

 Enter a strong password when prompted, and save this password somewhere safe as you will need it for any future changes to this file, as well as when you deploy and configuration changes to this machine.

### Add passwords to the vault file

In the vault file, change each field that has a value 'CHANGE ME' to a strong, unique password.

``` bash
$ ansible-vault edit ~/environments/monolith/vault.yml`
```

### Set the network interface name

1. Find the name of the network interface of your machine, and note it down. You can do this by running 

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
 
 Here, the network interface we are interested in is **enp0s3**. Note this value, or copy it to the system clipboard.

1. Open the `environments/monolith/inventory.ini` file, uncomment and set the value of `ufw_private_interface` to the network interface of your machine that we found in the previous step.

 ``` bash
 $ nano ./environments/monolith/inventory.ini
 ```

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


## Step 3

Install commcare-cloud onto the monolith as described in ./installation.md beginning with step 2.

## Step 4

```bash
COMMCARE_CLOUD_ENVIRONMENTS=/home/{username}/environments manage-commcare-cloud configure

#Let's get you set up to run commcare-cloud.

Do you work or contract for Dimagi? [y/N]n

To use commcare-cloud, you have to have an environments directory. This is where you will store information about your cluster setup, such as the IP addresses of the hosts in your cluster, how different services are distributed across the machines, and all settings specific to your CommCare instance.
I see you have COMMCARE_CLOUD_ENVIRONMENTS set to /home/{username}/environments in your environment
Would you like to use environments at that location? [y/N]y

echo "source ~/.commcare-cloud/load_config.sh" >> ~/.profile
```

## Step 5

```bash
sudo touch /var/log/ansible.log
sudo chmod 666 /var/log/ansible.log
commcare-cloud monolith update-local-known-hosts
```

## Step 6

Note: SSH password is the root user's password
After this step, the root user will not be able to log in via SSH

```bash
commcare-cloud monolith deploy-stack --first-time
This command will apply without running the check first. Continue? [y/N]y
ansible-playbook /home/jemord/commcare-cloud/src/commcare_cloud/ansible/deploy_stack.yml -i /home/jemord/environments/monolith/inventory.ini -e @/home/jemord/environments/monolith/vault.yml -e @/home/jemord/environments/monolith/public.yml -e @/home/jemord/environments/monolith/.generated.yml --diff --tags=bootstrap-users -u root --ask-pass --vault-password-file=/home/jemord/commcare-cloud/src/commcare_cloud/ansible/echo_vault_password.sh --ask-pass --ssh-common-args -o=UserKnownHostsFile=/home/jemord/environments/monolith/known_hosts
Vault Password for 'monolith': <password from encrypting vault.yml>
SSH password:<root user's password>
```

Note that there are occasionally timing issues when running this.
If you find an intermittent issue, or run into another issue that requires code changes,
you can run the following to continue the playbook once the issues are solved:

```bash
commcare-cloud monolith deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1'
```

## Step 7

Note: I've had some issues with preindex_everything failing

```bash
commcare-cloud monolith fab deploy
```

If this fails:

```bash
commcare-cloud monolith fab deploy:resume=yes
```

## Cleanup

CommCare Cloud will no longer need the root user to be accessible via the password. The password can be removed if you wish.
