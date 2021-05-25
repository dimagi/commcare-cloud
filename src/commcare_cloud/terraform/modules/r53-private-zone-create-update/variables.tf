variable "domain_name" {
  description = "Private Hosted zone name of the Route53 entry example: dev.dimagi.local"
}

variable "zone_vpc_id" {
  description = "Route-53 hosted zone associate VPC-ID"
}

variable "route_names" {
  description = "DNS names to be created example: dev-redis"
}

variable "type" {
  description = "Type of record in route53"
  type        = string
  default     = "CNAME"
}

variable "ttl" {
  description = "Time to live"
  type = number
  default     = 300
}

variable "records" {
  description = "List of records"
  type        = list
}

variable "create" {
  description = "Flag to enable/disable r53-private-zone-create-update"
  type        = bool
  default     = true
}

variable "create_record" {
  description = "Flag to enable/disable r53-private-zone-create record"
  type        = bool
  default     = true
}