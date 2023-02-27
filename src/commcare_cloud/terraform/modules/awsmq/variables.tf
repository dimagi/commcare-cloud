variable "broker_name" {
  description = "Name of the broker"
  type = string
}
variable "apply_immediately" {
  description = "Specifies whether any cluster modifications are applied immediately, or during the next maintenance window"
  type = bool
}
variable "auto_minor_version_upgrade"{
  description = "Enables automatic upgrades to new minor versions for brokers, as Apache releases the versions"
  type = bool
}
variable "deployment_mode" {
  description = "The deployment mode of the broker. Supported: SINGLE_INSTANCE and ACTIVE_STANDBY_MULTI_AZ"
  type = string
}
variable "engine_type" {
  description = "Type of broker engine, `ActiveMQ` or `RabbitMQ`"
  type = string 
}
variable "engine_version" {
  description = "The version of the broker engine."
  type = string
}
variable "host_instance_type" {
  description = "The broker's instance type. e.g. mq.t2.micro or mq.m4.large"
  type = string
}
variable "publicly_accessible" {
  description = "Whether to enable connections from applications outside of the VPC that hosts the broker's subnets"
  type = bool
}
variable "vpc_id" {
}
variable "encryption_enabled" {
  description = "Whether to enable connections from applications outside of the VPC that hosts the broker's subnets"
  type = bool
}
variable "username" {
  type        = string
  description = "(optional) description"
}
variable "password" {
  type        = string
  sensitive   = false
  description = "(optional) description"
}
variable "environment" {
  description = "environment"
  type = string
}
variable "account_alias" {
  description = "account_alias"
  type = string
}
variable "logs_general" {
  description = "Whether to enable general logs for cloudwatch"
  type = bool
}
variable "security_groups" {
  description = "A list of IDs of Security Groups to allow access to the security group created by this module. The length of this list must be known at \"plan\" time."
  type = list
}
variable "subnet_ids" {
  description = "List of VPC subnet IDs"
  type = list(string)
}