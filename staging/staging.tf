# This is the file that will define the basic function for the staging environment

data "terraform_remote_state" "staging_state" {
  backend = "s3"

  config {
    bucket  = "${var.tf_s3_bucket}"
    region  = "${var.state_region}"
    key     = "${var.staging_state_file}"
    encrypt = true
  }
}
