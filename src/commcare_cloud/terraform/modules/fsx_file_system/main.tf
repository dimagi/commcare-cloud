resource "aws_fsx_openzfs_file_system" "fsx_file_system" {
  count  = var.create == true ? 1 : 0
  storage_capacity    = var.storage_capacity
  subnet_ids          = var.fsx_subnet_ids
  deployment_type     = "SINGLE_AZ_1"
  throughput_capacity = var.throughput_capacity
  security_group_ids  = var.security_group_ids

  tags = {
    Name = var.fsx_name
    Environment = var.namespace
  }
}
