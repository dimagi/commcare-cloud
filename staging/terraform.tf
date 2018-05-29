# This is the base terraform.tf file.
# This should be used to identify the state file (preferrably in a shared location).

terraform {
  backend "s3" {
    bucket  = "g2-tf-commcarehq"
    key     = "g2-tf-commcarehq/state/staging/staging.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
