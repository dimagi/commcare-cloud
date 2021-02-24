output "mount_target_ids" {
  value       = "${join(",",aws_efs_mount_target.efs_mount_target.*.id)}"
  description = "List of EFS mount target IDs (one per Availability Zone)"
}

output "mount_dns_name" {
  value       = "${join(",",aws_efs_mount_target.efs_mount_target.*.dns_name)}"
  description = "The DNS name for the EFS file system"
}