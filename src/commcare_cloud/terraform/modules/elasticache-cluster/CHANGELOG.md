# elasticache-cluster-v0.1.3
[rameshganne] - Updated module to support Elasticache clsuter-enabled & clsuter-disabled.
# elasticache-cluster-v0.1.2
[rameshganne] - Updated module by removing snapshot_arn. It(snapshot_arn) can import db from s3 based rdb file but not working as we expecting ref: https://github.com/hashicorp/terraform-provider-aws/issues/5510.
# elasticache-cluster-v0.1.1
[rameshganne] - Updated module with snapshot_arn. It can import db from s3 based rdb file Example: arn:aws:s3:::my_bucket/snapshot1.rdb.
# elasticache-cluster-v0.1.0
[rameshganne] - Initial commit to create elasticache cluster with replication - Multi-AZ is not covering it.
