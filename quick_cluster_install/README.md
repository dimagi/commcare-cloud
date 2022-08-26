# Automated cluster setup

## Overview
This section briefly outlines the steps of how the automated cluster setup works. If you're not interested and simply wants to make 
it happen, skip this section.

High level steps:
1. User specifies what services should run on what machines (and how many machines)
2. The script invokes the `commcare_cloud_bootstrap.py` command to set up the machines on AWS and generate the 
environment files (e.g. `inventory.ini`, `app-processes.yml` etc.)
3. The script SSH into the control machine and pulls the `commcare-cloud` repo (so you don't have to)
4. Now you SSH into the control machine and run the `cchq-install` bash script (it's the same script used for 
the quick monolith install, but modified slightly for a cluster)

## Getting started
### Prerequisites
Make sure the aws cli tool is installed on your local machine

1) Add the following to `~/.aws/config`:

```
[profile commcare-cluster-test:session]
region = us-west-2
output = json

Add the following to ~/.aws/credentials:
[commcare-cluster-test]
aws_access_key_id = <access_key_id_from_keypass>
aws_secret_access_key = <secret_access_key_from_keypass>
```

2) Copy the commcarehq_cluster_testing.pem file to your local ssh directory (~/.ssh/). 
3) Branch from `automated-cluster-setup` and check out to that branch
4) Remember to run `source commcare-cloud/control/init.sh`

### Set up the cluster

Setting up the cluster basically involves
1) Configuring the cluster environment file
2) Provision machines
3) Deploy commcarehq from control machine

For the purposes of this process, let's suppose you want to create a new cluster environment called `cluster`.

#### Step 1: Configuring the cluster environment file
Change directory 
> cd quick_cluster_install/

(Optional) Run the following command:
> cp sample_environment.yml.sample cluster.yml 

Fill out the new environment's details. If this step is left out, the script will prompt you for the ncessary fields and create the file for you.

#### Step 2: Provision machines

After you've filled out the details in this new `cluster.yml` file, you simply run the following command to provision
the cluster machines on AWS:
> bash ./provision_machines.sh cluster [spec]

The script will do the following:
1) Check if the `cluster` environment exists; if not, it will simply copy the `sample_environment` environment. 
   The new environment's structure will look as follows:
    - _install_config.yml_: this file contains basic configurations, like the username of the user to set up on the server, etc.
    - _known_hosts_: this file is automatically created to be used during deploy.
    - _spec.yml_: this file contains the details of what the cluster looks like, i.e. what services sits on what machines, etc., and is used to provision the machines and populate the rest of the environment files necessary for a deploy.

> **_NOTE:_** 
> If you wish to specify your environment’s own spec.yml and not use the default spec.yml, you can either alter the default spec in the `sample_environment` 
> environment or create your own environment manually and specify the path to the spec when running the provision command.

The `control_machine_ip` will be output after the script has executed. You can also find the control machine's IP in the generated `inventory.ini` file.

#### Step 3: Deploy commcarehq from control machine
SSH into the remote control machine. If you want to do this later you can find the control machine’s IP in the newly created environment’s inventory.ini file (remember, you will need to specify the `.pem` identity file).

On the control machine, change directory:
> cd ~/commcare-cloud/quick_cluster_install/

and run the following:
> bash cchq-install.sh ./environments/cluster/install-config.yml


## Known issues
1) Sometimes the following commands of `cchq-install.sh` fail and you would have to execute it manaully:
   - commcare-cloud $env_name django-manage create_kafka_topics
   - commcare-cloud $env_name django-manage preindex_everything
