# This file (*.tfvars) defines the override variables for the environment.
region                = "us-east-1"
state_region          = "${var.region}"
environment           = "prod"
azs                   = ["{var.region}a","{var.region}b","{var.region}c"]
vpc_begin_range       = "10.20"
bastion_instance_type = "t2.micro"
openvpn_instance_type = "t2.small"
jenkins_instance_type = "t2.small"
openvpn_image         = "ami-cde8f721"
dns_domain            = ""                                                      # Set the DNS Domain name to be used (should match the name for the Zone ID)
dns_zone_id           = ""                                                      # Select the correct DNS Zone ID from Route 53
internal_ssl_cert_arn = ""                                                      # This will be used to reference SSL Certificate in AWS Certificate Manager

# If using RDS, uncomment and update as necessary
# #######
# # RDS #
# #######
# rds_storage                    = ""                                           # Setup the initial storage amount
# rds_engine                     = ""                                           # Specify the DB type; mysql, postgresql, aurora-mysql, etc
# rds_instance_type              = ""                                           # Select teh size of your RDS instance
# rds_username                   = ""                                           # Set the master username. rds_password should be passed via a secure method
# rds_storage_type               = "gp2"
# rds_backup_window              = "10:30-11:15"
# rds_backup_retention           = 30                                           # Keeps 30 days of snapshots
# rds_maintenance_window         = "wed:09:56-tue:10:26"
# rds_auto_minor_version_upgrade = false                                        # Whether or not to automatically update minor versions of the DB code, may cause service interruption.
# rds_multi_az                   = true                                         # Only set true on prod (or by request)
# rds_storage_encrypted          = true
# rds_port                       = ""                                           # DB listener port; 5432 = postgresql, 3306 = mysql
# rds_sg_ip_ingress              = ["${module.network.vpc-all-hosts-sg}"]
# rds_database_name              = "commcarehq"
# rds_prevent_destroy            = false
# rds_instance_count             = 1                                            # How many RDS instances to add to the cluster
# rds_engine_version             = ""                                           # Specific version to build
