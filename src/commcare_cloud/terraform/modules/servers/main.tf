resource aws_instance "server" {
  count                   = "${length(var.servers)}"
  ami                     = "${var.server_image}"
  instance_type           = "${lookup(var.servers[count.index], "server_instance_type")}"
  subnet_id               = "${var.subnet_options[
    format("%s-%s", lookup(var.servers[count.index], "network_tier"), lookup(var.servers[count.index], "az"))
  ]}"
  key_name                = "${var.key_name}"
  vpc_security_group_ids  = ["${var.security_group_options[lookup(var.servers[count.index], "network_tier")]}"]
  source_dest_check       = false
  credit_specification {
    cpu_credits = "unlimited"
  }
  root_block_device {
    volume_size           = "${lookup(var.servers[count.index], "volume_size")}"
    volume_type           = "gp2"
    delete_on_termination = true
  }
  lifecycle {
    ignore_changes = ["user_data", "key_name", "root_block_device.0.delete_on_termination", "ebs_optimized"]
  }
  tags {
    Name        = "${lookup(var.servers[count.index], "server_name")}"
    Environment = "${var.environment}"
  }
}
