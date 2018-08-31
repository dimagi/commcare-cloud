
# Dimagi Terraform VPC setup

1.  This setup will build out VPCs for dev, test, and prod.
    *   Each environment has it's own sub-directory, from which Terraform would need to be run.
2.  Remote state is setup to be stored in an S3 bucket.
    *   **NOTE**: The S3 bucket needs to be created prior to running Terraform, otherwise it will generate errors.
    *   **IMPORTANT**: When creating the S3 bucket for a specific region, ensure that all state file and region references are in alignment.
3.  Each environment directory links to the top level _initialize.tf_ and _variables.tf_ files.
    *   These linked files, should be generic instantiation files and setting of default values.
    *   The _terraform.tf_ and environment.tf files will define the specific S3 State information for that environment.
    *   The environment's **tfvars** is the variables file that overrides the default values in variables.tf.
4.  The _modules_ directory contains the modules that that we commonly use in a Terraform stack.
    *   All Terraform stacks should contain at least a **network** module to stand up the initial VPC, even if it is just a single environment.
    *   Additional modules can be added as needed. Ideally, they will use similar variable naming conventions to facilitate re-use.
    *   Common modules are:
        *   **bastion** for creating a bastion host in the environment.
        *   **jenkins** to use as an automation hub for managing the environment.
        *   **openvpn** to limit access into systems in the VPC.
        *   **rds** to spin up a database to be used in the environment.
            *   **aurora-cluster** to specifically spin up an Aurora Cluster in RDS.
