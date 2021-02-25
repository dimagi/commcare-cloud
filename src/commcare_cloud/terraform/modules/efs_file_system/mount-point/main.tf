resource "aws_efs_mount_target" "efs_mount_target" {
  count  = "${var.create_mount == "true" ? 1 : 0}"
  file_system_id = "${var.file_system_id}"
  subnet_id      = "${var.subnet_ids_efs}"
  security_groups = ["${var.securitygroup_id}"]
}
