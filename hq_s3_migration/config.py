from dataclasses import dataclass

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
    enable_rtc: bool = True  # S3 Replication Time Control (15-min SLA)
    enable_delete_replication: bool = True


ACCOUNT_IDS = {
    'production': '051428382917',
    'staging': '737236193635',
    'backup-production': '213307118311',
    'dimagi':'437781348816'
}

ACCOUNT_NAMES = {v: k for k, v in ACCOUNT_IDS.items()}
