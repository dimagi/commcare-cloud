# Setting up a new CommCare environment

This document will walk you through the process of setting up a new monolith server to run HQ

## Pre-requesites

* A server with Ubuntu 18.04 installed (referred to as the "monolith" from here)
* Access to the monolith via SSH via root user & password
* A cloned copy of a monolith environment such as https://github.com/emord/supreme-octo-potato.git
* An ssh key pair

## Step 1

Install pip on the monolith

```bash
sudo apt install python-pip
sudo pip install ansible virtualenv virtualenvwrapper --ignore-installed six
```

## Step 2 Configure your environment

```bash
git clone https://github.com/emord/supreme-octo-potato.git environments
```

Encrypt the provided ansible vault file:

`ansible-vault encrypt ~/environments/monolith/vault.yml`

Save this password somewhere safe as you will need it for any future changes to this file,
and all ansible deploys.

Change all fields in the vault file that have the value 'CHANGE ME'

`ansible-vault edit ~/environments/monolith/vault.yml`

Change `ufw_private_interface` to the network interface of your machine (found via `ip addr`)
and the ip address for the monolith group in inventory.ini file.

Add your user's public key to `~/environments/_authorized_keys`. And username to `dimagi.yml`

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
