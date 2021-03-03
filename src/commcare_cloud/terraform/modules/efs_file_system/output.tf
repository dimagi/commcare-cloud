output "efs_endpoint_address" {
  value = "${aws_efs_file_system.elastic_file_system.*.dns_name}"
}

output "efs_id" {
  value = "${join(",",aws_efs_file_system.elastic_file_system.*.id)}"
}
