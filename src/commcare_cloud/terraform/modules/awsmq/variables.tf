variable "broker_name" {
  description = "Name of the broker"
  type = string
}
variable "broker_apply_immediately" {
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
variable "allowed_security_group_ids" {
  description = "A list of IDs of Security Groups to allow access to the security group created by this module. The length of this list must be known at "plan" time."
  type = string
}
variable "vpc_id" {
  description = "The ID of the VPC to create the broker in"
  type = string
}
variable "subnet_ids" {
  description = "List of VPC subnet IDs"
  type = list
}