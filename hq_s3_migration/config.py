from dataclasses import dataclass


def derive_resource_names(source_env: str, dest_env: str) -> dict:
    """Derive all per-migration resource names from env-name aliases."""
    suffix = f"{source_env}-to-{dest_env}"
    return {
        "replication_role_name": f"s3-replication-role-{suffix}",
        "datasync_role_name": f"datasync-s3-role-{suffix}",
        "report_bucket_name": f"s3-migration-{suffix}-datasync-run-reports",
        "report_role_name": f"datasync-report-role-{suffix}",
        "failures_queue_name": f"s3-replication-failures-{suffix}",
        "threshold_queue_name": f"s3-replication-threshold-{suffix}",
    }


@dataclass
class MigrationConfig:
    """Configuration for S3 cross-account migration."""
    source_profile: str
    dest_profile: str
    source_bucket: str
    dest_bucket: str
    source_account_id: str
    dest_account_id: str
    region: str
    replication_role_name: str
    datasync_role_name: str
    report_bucket_name: str
    report_role_name: str
    failures_queue_name: str
    threshold_queue_name: str
    enable_rtc: bool = True  # S3 Replication Time Control (15-min SLA)
    enable_delete_replication: bool = True


ACCOUNT_IDS = {
    'production': '051428382917',
    'staging': '737236193635',
    'backup-production': '213307118311',
    'dimagi':'437781348816'
}

ACCOUNT_NAMES = {v: k for k, v in ACCOUNT_IDS.items()}
