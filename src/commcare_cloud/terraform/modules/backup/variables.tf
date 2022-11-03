variable "environment" {}

variable "region" {}

variable "account_id" {}

variable "local_vault_name" {}
variable "remote_vault_name" {}
variable "remote_vault_region" {}

variable "outside_account_id" {}

variable "daily_retention" {
  type = number
}

variable "monthly_retention" {
  type = number
}

variable "quarterly_retention" {
  type = number
}
