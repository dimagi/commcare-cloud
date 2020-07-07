// for global accelerator which can only be configured in us-west-2
provider "aws" {
  alias = "us-west-2"
  region = "us-west-2"
}
