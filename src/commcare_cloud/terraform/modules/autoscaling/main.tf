resource "aws_s3_bucket" "deploy_archive_bucket" {
  bucket = var.release_bucket
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deploy_archive_bucket" {
  bucket = aws_s3_bucket.deploy_archive_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "deploy_archive_bucket" {
  bucket = aws_s3_bucket.deploy_archive_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "deploy_archive_bucket" {
  bucket = aws_s3_bucket.deploy_archive_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role_policy" "access_deploy_archive" {
  name = "AccessDeployArchive"
  role = var.commcare_server_role_id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Terraform0",
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObjectTagging",
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucketVersions",
                "s3:GetObjectTagging",
                "s3:ListBucket",
                "s3:PutObjectTagging",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::${var.release_bucket}/*",
                "arn:aws:s3:::${var.release_bucket}"
            ]
        }
    ]
}
  POLICY
}
