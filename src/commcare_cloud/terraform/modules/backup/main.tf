terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      configuration_aliases = [
        aws.remote_region,
      ]
    }
  }
}

resource "aws_backup_plan" "business_continuity_plan" {
  name = "BusinessContinuity"

  rule {
    completion_window        = 10080
    enable_continuous_backup = false
    rule_name                = "Daily"
    schedule                 = "cron(0 1 ? * * *)"
    start_window             = 60
    target_vault_name        = aws_backup_vault.business_continuity_local_vault.name

    copy_action {
      destination_vault_arn = aws_backup_vault.business_continuity_remote_vault.arn

      lifecycle {
        cold_storage_after = 0
        delete_after = var.daily_retention
      }
    }

    lifecycle {
      delete_after = 1
    }
  }
  rule {
    completion_window        = 10080
    enable_continuous_backup = false
    rule_name                = "Monthly"
    schedule                 = "cron(0 13 ? * 1#1 *)"
    start_window             = 60
    target_vault_name        = aws_backup_vault.business_continuity_local_vault.name

    copy_action {
      destination_vault_arn = aws_backup_vault.business_continuity_remote_vault.arn

      lifecycle {
        cold_storage_after = 1
        delete_after = var.monthly_retention
      }
    }

    lifecycle {
      delete_after = 1
    }
  }
}

resource "aws_backup_vault" "business_continuity_local_vault" {
  name        = var.local_vault_name
  kms_key_arn = aws_kms_key.business_continuity_local_vault_key.arn
}

resource "aws_backup_vault" "business_continuity_remote_vault" {
  name        = var.remote_vault_name
  provider = aws.remote_region
  kms_key_arn = aws_kms_key.business_continuity_remote_vault_key.arn
}

resource "aws_kms_key" "business_continuity_local_vault_key" {
}

resource "aws_kms_key" "business_continuity_remote_vault_key" {
  provider = aws.remote_region
}

resource "aws_backup_vault_policy" "business_continuity_local_vault_policy" {
  backup_vault_name = aws_backup_vault.business_continuity_local_vault.name

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "backup:CopyIntoBackupVault",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:PrincipalOrgID": "${var.org_id}"
                }
            }
        }
    ]
}
POLICY
}
resource "aws_backup_vault_policy" "business_continuity_remote_vault_policy" {
  provider = aws.remote_region

  backup_vault_name = aws_backup_vault.business_continuity_remote_vault.name

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "backup:CopyIntoBackupVault",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:PrincipalOrgID": "${var.org_id}"
                }
            }
        },
        {
            "Sid": "0cfc19f4-bec0-4a37-8bf8-6d15b3650f66",
            "Effect": "Allow",
            "Principal": {
                "AWS": "AROATDKQYKLTTBKSMZN3Z"
            },
            "Action": [
                "backup:CopyIntoBackupVault",
                "backup:CopyFromBackupVault",
                "backup:DeleteRecoveryPoint",
                "backup:ListRecoveryPointsByBackupVault"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_backup_selection" "business_continuity_plan_selection" {
  iam_role_arn = "arn:aws:iam::${var.account_id}:role/service-role/AWSBackupDefaultServiceRole"
  name         = "BusinessContinuity"
  plan_id      = aws_backup_plan.business_continuity_plan.id

  resources = []

  selection_tag {
    key   = "BackupPlan"
    type  = "STRINGEQUALS"
    value = "BusinessContinuity"
  }
}
