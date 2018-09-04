# This is the base terraform.tf file.
# This should be used to identify the state file (preferrably in a shared location).

terraform {
  backend "s3" {
    bucket  = "g2-tftf-state"
    key     = "terraform-g2-tf/state/prod/prod.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
