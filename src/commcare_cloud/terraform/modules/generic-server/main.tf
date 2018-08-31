resource aws_instance "server" {
  ami                    = "${var.server_image}"
  instance_type          = "${var.server_instance_type}"
  subnet_id              = "${var.instance_subnet}"
  key_name               = "g2-access"
  vpc_security_group_ids = ["${var.security_groups}"]
  source_dest_check      = false
  root_block_device {
    volume_size           = 20
    volume_type           = "gp2"
    delete_on_termination = true
  }
  tags {
    Name        = "${var.server_name}"
    Environment = "${var.environment}"
#    Service     = "${var.service}"
  }
  user_data = <<-EOF
    #!/bin/bash
    hostnamectl set-hostname "${var.server_name}"
    yum update -y
    reboot
    EOF
}
