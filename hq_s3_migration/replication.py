from botocore.exceptions import ClientError

from .orchestrator import S3MigrationContext


def enable_live_replication(ctx: S3MigrationContext) -> bool:
    """Enable S3 live replication from source to destination."""
    cfg = ctx.config

    print("\n" + "=" * 60)
    print("PHASE 2: Enabling S3 Live Replication")
    print("=" * 60)

    role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.replication_role_name}"

    rule = {
        'ID': 'CrossAccountReplication',
        'Status': 'Enabled',
        'Priority': 1,
        'Filter': {},
        'Destination': {
            'Bucket': f'arn:aws:s3:::{cfg.dest_bucket}',
            'Account': cfg.dest_account_id,
            'StorageClass': 'INTELLIGENT_TIERING',
            'AccessControlTranslation': {
                'Owner': 'Destination'
            }
        },
        'DeleteMarkerReplication': {
            'Status': 'Enabled' if cfg.enable_delete_replication else 'Disabled'
        }
    }

    if cfg.enable_rtc:
        rule['Destination']['ReplicationTime'] = {
            'Status': 'Enabled',
            'Time': {'Minutes': 15}
        }
        rule['Destination']['Metrics'] = {
            'Status': 'Enabled',
            'EventThreshold': {'Minutes': 15}
        }

    replication_config = {
        'Role': role_arn,
        'Rules': [rule]
    }

    print(f"\nConfiguring replication rule...")
    print(f"  Source: {cfg.source_bucket}")
    print(f"  Destination: {cfg.dest_bucket}")
    print(f"  Delete replication: {'Enabled' if cfg.enable_delete_replication else 'Disabled'}")
    print(f"  RTC (15-min SLA): {'Enabled' if cfg.enable_rtc else 'Disabled'}")

    try:
        ctx.source_s3.put_bucket_replication(
            Bucket=cfg.source_bucket,
            ReplicationConfiguration=replication_config
        )
        print(f"\n  SUCCESS: Live replication enabled")
        print(f"  All NEW objects will now replicate automatically")
        return True
    except ClientError as e:
        print(f"\n  ERROR: {e}")
        return False


def get_replication_status(ctx: S3MigrationContext) -> dict:
    """Get current replication configuration and status."""
    print("\nChecking replication status...")

    result = {
        'configured': False,
        'rules': [],
        'metrics': None
    }

    try:
        config = ctx.source_s3.get_bucket_replication(Bucket=ctx.config.source_bucket)
        result['configured'] = True
        result['rules'] = config['ReplicationConfiguration']['Rules']
        print(f"  Replication is configured")
        for rule in result['rules']:
            print(f"    Rule '{rule['ID']}': {rule['Status']}")
    except ClientError as e:
        if 'ReplicationConfigurationNotFoundError' in str(e):
            print(f"  Replication is NOT configured")
        else:
            print(f"  ERROR: {e}")

    return result


def disable_replication(ctx: S3MigrationContext) -> bool:
    """Disable S3 replication rule."""
    print("\nDisabling replication...")

    try:
        ctx.source_s3.delete_bucket_replication(Bucket=ctx.config.source_bucket)
        print(f"  Replication disabled")
        return True
    except ClientError as e:
        print(f"  ERROR: {e}")
        return False
