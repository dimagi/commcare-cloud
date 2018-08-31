# This is the file that will define the basic function for the prod environment

data "terraform_remote_state" "prod_state" {
  backend = "s3"

  config {
    bucket  = "${var.tf_s3_bucket}"
    region  = "${var.state_region}"
    key     = "${var.prod_state_file}"
    encrypt = true
  }
}
