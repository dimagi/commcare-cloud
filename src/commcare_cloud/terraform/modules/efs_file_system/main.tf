resource "aws_efs_file_system" "elastic_file_system" {
  count  = "${var.create == "true" ? 1 : 0}"
  encrypted = true
  lifecycle_policy {
    transition_to_ia = "${var.transition_to_ia}"
  }
  tags = {
    Name = "${var.efs_name}-${var.namespace}-efs"
  }
}

resource "aws_efs_access_point" "efs_access_point" {
  count  = "${var.create_access == "true" ? 1 : 0}"
  file_system_id = "${aws_efs_file_system.elastic_file_system.id}"
}
