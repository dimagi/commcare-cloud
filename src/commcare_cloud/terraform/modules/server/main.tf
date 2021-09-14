resource aws_instance "server" {
  ami                     = var.server_image
  instance_type           = var.server_instance_type
  subnet_id               = var.subnet_options[
    format("%s-%s", var.network_tier, var.az)
  ]
  key_name                = var.key_name
  vpc_security_group_ids  = compact(var.security_group_options[var.network_tier])
  source_dest_check       = false
  iam_instance_profile    = var.iam_instance_profile

  disable_api_termination = true
  ebs_optimized = true
  root_block_device {
    volume_size           = var.volume_size
    encrypted             = var.volume_encrypted
    volume_type           = var.volume_type
    delete_on_termination = true
    tags = {
      Name = "vol-${var.server_name}"
      ServerName = var.server_name
      Environment = var.environment
      Group = var.group_tag
    }
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
   lifecycle {
    ignore_changes = [
      # temporarily ignore the "BackupPlan" tag until it's managed properly
      tags,
      tags.BackupPlan
      ]
  }
}

resource "aws_volume_attachment" "ebs_att" {
  count = var.secondary_volume_size > 0 ? 1 : 0
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.ebs_volume[count.index].id
  instance_id = aws_instance.server.id
}

data "aws_region" "current" {
}

data "aws_partition" "current" {
}

resource "aws_cloudwatch_metric_alarm" "auto-recover-instance" {
  count   = var.server_auto_recovery == true ? 1 : 0
  alarm_name          = format(var.name_format_instance, var.server_name, count.index + 1)
  metric_name         = "StatusCheckFailed_Instance"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"

  dimensions = {
    InstanceId = aws_instance.server.id
  }

  namespace         = "AWS/EC2"
  period            = "60"
  statistic         = "Minimum"
  threshold         = "0"
  alarm_description = "Auto-recover the instance if the Instance status check fails for two minutes"
  alarm_actions = compact(
    concat(
      [
        "arn:${data.aws_partition.current.partition}:automate:${data.aws_region.current.name}:ec2:reboot",
      ],
      var.alarm_actions,
    ),
  )
}

resource "aws_cloudwatch_metric_alarm" "auto-recover-system" {
  count   = var.server_auto_recovery == true ? 1 : 0
  alarm_name          = format(var.name_format_system, var.server_name, count.index + 1)
  metric_name         = "StatusCheckFailed_System"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"

  dimensions = {
    InstanceId = aws_instance.server.id
  }

  namespace         = "AWS/EC2"
  period            = "60"
  statistic         = "Minimum"
  threshold         = "0"
  alarm_description = "Auto-recover the instance if the system status check fails for two minutes"
  alarm_actions = compact(
    concat(
      [
        "arn:${data.aws_partition.current.partition}:automate:${data.aws_region.current.name}:ec2:recover",
      ],
      var.alarm_actions,
    ),
  )
}
