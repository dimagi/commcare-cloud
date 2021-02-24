resource "aws_efs_mount_target" "efs_mount_target" {
  file_system_id = "${var.file_system_id}"
  subnet_id      = "${var.subnet_ids_efs}"
  security_groups = ["${var.securitygroup_id}"]
}