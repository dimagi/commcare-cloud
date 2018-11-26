resource aws_instance "server" {
  ami                     = "${var.server_image}"
  instance_type           = "${var.server_instance_type}"
  subnet_id               = "${var.subnet_options[
    format("%s-%s", var.network_tier, var.az)
  ]}"
  key_name                = "${var.key_name}"
  vpc_security_group_ids  = ["${var.security_group_options[var.network_tier]}"]
  source_dest_check       = false
  credit_specification {
    cpu_credits = "unlimited"
  }
  root_block_device {
    volume_size           = "${var.volume_size}"
    volume_type           = "gp2"
    delete_on_termination = true
  }
  lifecycle {
    ignore_changes = ["user_data", "key_name", "root_block_device.0.delete_on_termination", "ebs_optimized", "ami"]
  }
  tags {
    Name        = "${var.server_name}"
    Environment = "${var.environment}"
  }
}
