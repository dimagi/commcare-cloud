variable "environment" {
}

variable "security_groups" {
  type = list(string)
}

variable "subnets" {
  type = list(string)
}

variable "vpc_id" {
}

variable "SITE_HOST" {
}

variable "NO_WWW_SITE_HOST" {
}

variable "ALTERNATE_HOSTS" {
  type = list(string)
}

variable "proxy_server_ids" {
  type = list(string)
}

variable "account_id" {
}

variable "ssl_policy" {
}

variable "commcarehq_xml_post_urls_regex" {
  type = list(map(string))
}

variable "commcarehq_xml_querystring_urls_regex" {
  type = list(map(string))
}

variable "log_bucket_name" {
}

variable "log_bucket_arn" {
}

