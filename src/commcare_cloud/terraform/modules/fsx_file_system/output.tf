output "fsx_endpoint_address" {
  value = "${aws_fsx_openzfs_file_system.fsx_file_system.*.dns_name}"
}

output "efs_id" {
  value = "${join(",",aws_fsx_openzfs_file_system.fsx_file_system.*.id)}"
}
