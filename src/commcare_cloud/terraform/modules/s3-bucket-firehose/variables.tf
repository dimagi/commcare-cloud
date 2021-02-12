variable "bucket_name" {
  description = "The name of the bucket. It must be a unique name. Must be less than or equal to 63 characters in length."
}

variable "canned_acl_type" {
  description = "The canned ACL to apply. Valid values are private, public-read, public-read-write, aws-exec-read, authenticated-read, and log-delivery-write. Defaults to private"
  default     = "private"
}

variable "sse_algorithm_use" {
  description = "The server-side encryption algorithm to use. Valid values are AES256 and aws:kms"
  default     = "AES256"
}

variable "region" {
  description = "The AWS region ID"
}

variable "create" {}
