## Automated cluster setup

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

2) Copy the commcarehq_cluster_testing.pem file to your local ssh directory. 


### Set up the cluster

Setting up the cluster basically involves
1) Configuring the cluster environment file
2) Provision machines
3) Deploy commcarehq from control machine

> **_NOTE:_** 
> Branch from `automated-cluster-setup` and checkout to that branch before you begin

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
> ./provision_machines.sh cluster

The script will do the following:
1) Check if the `cluster` environment exists; if not, it will simply copy the `sample_environment` environment. 
   The new environment's structure will look as follows:
    - _install_config.yml_: this file contains basic configurations, like the username of the user to set up on the server, etc.
    - _known_hosts_: this file is automatically created to be used during deploy.
    - _spec.yml_: this file contains the details of what the cluster looks like, i.e. what services sits on what machines, etc., and is used to provision the machines and populate the rest of the environment files necessary for a deploy.

> **_NOTE:_** 
> If you wish to specify your environment’s own spec.yml and not use the default spec.yml, you can either alter the default spec in the `sample_environment` 
> environment or create your own environment manually and specify it there. if you decide to create your own environment manually, please take notice of the file structure mentioned above.

#### Step 3: Deploy commcarehq from control machine
When the script is done, follow the output command to ssh into the remote control machine. If you want to do this later you can find the control machine’s IP in the newly created environment’s inventory.ini file (remember, you will need to specify the `.pem` identity file).

On the control machine, change directory:
> cd ~/commcare-cloud/quick_cluster_install/

and run the following:
> bash cchq-install.sh ./environments/cluster/install-config.yml