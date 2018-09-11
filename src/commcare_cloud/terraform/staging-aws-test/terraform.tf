terraform {
  backend "s3" {
    bucket  = "dimagi-terraform"
    key     = "state/staging-test.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region  = "us-east-1"
}

variable "rds_password" {
  type = "string"
}

module "commcarehq" {
  source = "../modules/commcarehq"
  region = "us-east-1"
  environment = "staging-test"
  company = "dimagi"
  azs = ["us-east-1a", "us-east-1b", "us-east-1c"]
  vpc_begin_range = "10.200"
  dns_domain = ""
  # Set the DNS Domain name to be used (should match the name for the Zone ID)
  dns_zone_id = ""
  # Select the correct DNS Zone ID from Route 53
  internal_ssl_cert_arn = ""
  # This will be used to reference SSL Certificate in AWS Certificate Manager
  external_routes = [
    {
      cidr_block = "172.24.16.0/22"
      gateway_id = "vgw-8dd726e4"
    },
    {
      cidr_block = "172.24.32.0/22"
      gateway_id = "vgw-8dd726e4"
    },
  ]

  servers = [
    {
      server_name = "web0-staging"
      server_instance_type = "t2.micro"
      network_tier = "app-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "web1-staging"
      server_instance_type = "t2.micro"
      network_tier = "app-private"
      az = "b"
      volume_size = 20
    },
    {
      server_name = "celery0-staging"
      server_instance_type = "t2.large"
      network_tier = "app-private"
      az = "b"
      volume_size = 20
    },
    {
      server_name = "pillow0-staging"
      server_instance_type = "t2.large"
      network_tier = "app-private"
      az = "c"
      volume_size = 20
    },
    {
      server_name = "formplayer0-staging"
      server_instance_type = "t2.micro"
      network_tier = "app-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "kafka0-staging"
      server_instance_type = "t2.medium"
      network_tier = "db-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "es0-staging"
      server_instance_type = "t2.micro"
      network_tier = "db-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "airflow0-staging"
      server_instance_type = "t2.micro"
      network_tier = "app-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "rabbit0-staging"
      server_instance_type = "t2.micro"
      network_tier = "db-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "pgproxy0-staging"
      server_instance_type = "t2.medium"
      network_tier = "app-private"
      az = "a"
      volume_size = 20
    },
    {
      server_name = "control-staging"
      server_instance_type = "t2.medium"
      network_tier = "app-private"
      az = "a"
      volume_size = 8
    },
  ]

  proxy_servers = [
    {
      server_name = "proxy1-staging"
      server_instance_type = "t2.medium"
      network_tier = "public"
      az = "b"
      volume_size = 20
    },
  ]

  rds_instances = [
    {
      password = "${var.rds_password}"
      identifier = "staging"
      instance_type = "db.t2.medium"
      storage = 300
    },
  ]
}
