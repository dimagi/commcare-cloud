terraform {
  backend "s3" {
    bucket  = "dimagi-terraform"
    key     = "state/staging.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region  = "us-east-1"
}


module "commcarehq" {
  source = "../modules/commcarehq"
  region                = "us-east-1"
  environment           = "staging"
  company               = "dimagi"
  azs                   = ["us-east-1a","us-east-1b","us-east-1c"]
  vpc_begin_range       = "10.200"
  dns_domain            = ""                        # Set the DNS Domain name to be used (should match the name for the Zone ID)
  dns_zone_id           = ""                        # Select the correct DNS Zone ID from Route 53
  internal_ssl_cert_arn = ""                        # This will be used to reference SSL Certificate in AWS Certificate Manager

  # Redis/ElastiCache variables
  redis_node_type      = "cache.t2.small"
  num_redis_nodes      = 1
  engine_version       = "4.0.10"
  redis_subnet_group   = "g2-tf-a-util-private-staging"
  parameter_group_name = "default.redis4.0"

  servers = [
    {
      server_name           = "django"
      server_instance_type  = "t2.micro"
      subnet_index          = 0
    },
    {
      server_name           = "django1"
      server_instance_type  = "t2.micro"
      subnet_index          = 1
    },
    {
      server_name           = "celery"
      server_instance_type  = "t2.large"
      subnet_index          = 1
    },
    {
      server_name           = "pillowtop"
      server_instance_type  = "t2.large"
      subnet_index          = 2
    },
    {
      server_name           = "formplayer"
      server_instance_type  = "t2.micro"
      subnet_index          = 0
    },
    {
      server_name           = "kafka"
      server_instance_type  = "t2.medium"
      subnet_index          = 0
    },
    {
      server_name           = "ES"
      server_instance_type  = "t2.micro"
      subnet_index          = 0
    },
    {
      server_name           = "Airflow"
      server_instance_type  = "t2.micro"
      subnet_index          = 0
    },
    {
      server_name           = "RabbitMQ"
      server_instance_type  = "t2.micro"
      subnet_index          = 0
    },
    {
      server_name           = "PG_Proxy"
      server_instance_type  = "t2.medium"
      subnet_index          = 0
    },
    {
      server_name           = "control"
      server_instance_type  = "t2.medium"
      subnet_index          = 3
      volume_size           = 8
    }
  ]

  proxy_servers = [
    {
      server_name           = "Proxy"
      server_instance_type  = "t2.medium"
      subnet_index          = 0
    }
  ]


  # If using RDS, uncomment and update as necessary
  # #######
  # # RDS #
  # #######
  # rds_storage                    = "330"                                      # Setup the initial storage amount
  # rds_engine                     = "postgresql"                                 # Specify the DB type; mysql, postgresql, aurora-mysql, etc
  # rds_instance_type              = "db.t2.micro"                                   # Select teh size of your RDS instance
  # rds_username                   = "root"                                       # Set the master username. rds_password should be passed via a secure method
  # rds_storage_type               = "gp2"
  # rds_backup_window              = "10:30-11:15"
  # rds_backup_retention           = 7                                           # Keeps 30 days of snapshots
  # rds_maintenance_window         = "sat:09:56-sun:10:26"
  # rds_auto_minor_version_upgrade = false                                        # Whether or not to automatically update minor versions of the DB code, may cause service interruption.
  # rds_multi_az                   = false                                        # Only set true on prod (or by request)
  # rds_storage_encrypted          = true
  # rds_port                       = "5432"                                       # DB listener port; 5432 = postgresql, 3306 = mysql
  # rds_sg_ip_ingress              = ["${module.network.vpc-all-hosts-sg}"]
  # rds_database_name              = "commcarehq"
  # rds_prevent_destroy            = false
  # rds_instance_count             = 1                                            # How many RDS instances to add to the cluster
  # rds_engine_version             = "9.6.8-R1"                                   # Specific version to build

}
