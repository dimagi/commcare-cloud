terraform {
  backend "s3" {
    bucket  = "dimagi-terraform"
    key     = "state/staging.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
