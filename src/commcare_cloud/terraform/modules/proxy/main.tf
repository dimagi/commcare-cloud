resource aws_instance "server" {
  ami                    = "${var.server_image}"
  instance_type          = "${var.server_instance_type}"
  subnet_id              = "${var.instance_subnet}"
  key_name               = "g2-access"
  vpc_security_group_ids = ["${var.proxy-sg}"]
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

resource "aws_eip" "proxy" {
  vpc = true
  instance = "${aws_instance.server.id}"
  associate_with_private_ip = "${aws_instance.server.private_ip}"
}
