resource aws_instance "server" {
  ami                     = var.server_image
  instance_type           = var.server_instance_type
  subnet_id               = var.subnet_options[
    format("%s-%s", var.network_tier, var.az)
  ]
  key_name                = var.key_name
  vpc_security_group_ids  = var.security_group_options[var.network_tier]
  source_dest_check       = false
  iam_instance_profile    = var.iam_instance_profile

  disable_api_termination = true
  ebs_optimized = true
  root_block_device {
    volume_size           = var.volume_size
    encrypted             = var.volume_encrypted
    volume_type           = var.volume_type
    delete_on_termination = true
  }
  lifecycle {
    ignore_changes = [user_data, key_name, root_block_device.0.delete_on_termination,
      ebs_optimized, ami, volume_tags, iam_instance_profile]
  }
  tags = {
    Name        = var.server_name
    Environment = var.environment
    Group = var.group_tag
  }
  volume_tags = {
    Name = "vol-${var.server_name}"
    ServerName = var.server_name
    Environment = var.environment
    Group = var.group_tag
  }
  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
    http_tokens                 = var.metadata_tokens
  }

}

resource "aws_ebs_volume" "ebs_volume" {
  count = var.secondary_volume_size > 0 ? 1 : 0
  availability_zone = aws_instance.server.availability_zone
  size = var.secondary_volume_size
  type = var.secondary_volume_type
  encrypted = var.secondary_volume_encrypted

  tags = {
    Name = "data-vol-${var.server_name}"
    ServerName = var.server_name
    Environment = var.environment
    Group = var.group_tag
    VolumeType = "data"
    GroupDetail = "${var.group_tag}:data"
  }
}

resource "aws_volume_attachment" "ebs_att" {
  count = var.secondary_volume_size > 0 ? 1 : 0
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.ebs_volume[count.index].id
  instance_id = aws_instance.server.id
}
