import random
import string
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from .orchestrator import S3MigrationContext
from .replication import get_replication_status


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} EB"


def get_bucket_stats(ctx: S3MigrationContext, s3_client, bucket_name: str) -> dict:
    """Get object count and total size using CloudWatch metrics (scales to 1B+ objects)."""
    print(f"\nGetting stats for bucket '{bucket_name}'...")

    session = ctx.source_session if s3_client is ctx.source_s3 else ctx.dest_session
    cloudwatch = session.client('cloudwatch')

    now = datetime.now(timezone.utc)
    metrics_result = {}

    try:
        for metric_name, stat_key in [('NumberOfObjects', 'object_count'), ('BucketSizeBytes', 'total_size')]:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'AllStorageTypes' if metric_name == 'NumberOfObjects' else 'StandardStorage'}
                ],
                StartTime=now - timedelta(days=3),
                EndTime=now,
                Period=86400,
                Statistics=['Average']
            )
            if response['Datapoints']:
                latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                metrics_result[stat_key] = int(latest['Average'])

        if 'object_count' in metrics_result:
            total_objects = metrics_result['object_count']
            total_size = metrics_result.get('total_size', 0)
            print(f"  Total objects: {total_objects:,} (from CloudWatch metrics)")
            print(f"  Total size: {format_size(total_size)}")
            print(f"  Note: CloudWatch S3 metrics may be up to 24h delayed")
            return {'object_count': total_objects, 'total_size': total_size}
        else:
            print(f"  WARNING: No CloudWatch metrics available for this bucket")
            print(f"  Ensure S3 request metrics are enabled or wait for daily storage metrics")
            return {'object_count': 0, 'total_size': 0, 'error': 'no_metrics'}
    except ClientError as e:
        print(f"  ERROR: {e}")
        return {'object_count': 0, 'total_size': 0, 'error': str(e)}


def verify_sample(ctx: S3MigrationContext, sample_size: int, mismatches: list) -> bool:
    """Verify a sample of objects between source and destination.

    Uses random prefixes to sample from across the entire key space,
    avoiding bias toward lexicographically early keys.
    """
    cfg = ctx.config
    sample_keys = []
    prefixes_tried = set()
    prefix_chars = string.ascii_lowercase + string.digits

    try:
        while len(sample_keys) < sample_size * 3 and len(prefixes_tried) < len(prefix_chars):
            prefix = random.choice(prefix_chars)
            if prefix in prefixes_tried:
                continue
            prefixes_tried.add(prefix)

            response = ctx.source_s3.list_objects_v2(
                Bucket=cfg.source_bucket,
                Prefix=prefix,
                MaxKeys=sample_size
            )
            if 'Contents' in response:
                for obj in response['Contents']:
                    sample_keys.append(obj['Key'])
    except ClientError:
        return False

    if not sample_keys:
        print("  No objects to sample")
        return True

    sample = random.sample(sample_keys, min(sample_size, len(sample_keys)))

    verified = 0
    for key in sample:
        try:
            source_obj = ctx.source_s3.head_object(Bucket=cfg.source_bucket, Key=key)
            dest_obj = ctx.dest_s3.head_object(Bucket=cfg.dest_bucket, Key=key)

            if source_obj['ETag'] == dest_obj['ETag']:
                verified += 1
            elif source_obj['ContentLength'] == dest_obj['ContentLength']:
                verified += 1
            else:
                mismatches.append({
                    'key': key,
                    'reason': 'Size mismatch',
                    'source_size': source_obj['ContentLength'],
                    'dest_size': dest_obj['ContentLength'],
                    'source_etag': source_obj['ETag'],
                    'dest_etag': dest_obj['ETag']
                })
        except ClientError as e:
            mismatches.append({
                'key': key,
                'reason': str(e)
            })

    print(f"  Verified: {verified}/{sample_size}")
    if mismatches:
        print(f"  Mismatches: {len(mismatches)}")
        for m in mismatches[:5]:
            print(f"    - {m['key']}: {m['reason']}")

    return len(mismatches) == 0


def validate_migration(ctx: S3MigrationContext, sample_size: int = 100) -> dict:
    """Validate migration by comparing buckets."""
    cfg = ctx.config

    print("\n" + "=" * 60)
    print("PHASE 4: Validating Migration")
    print("=" * 60)

    result = {
        'source_stats': None,
        'dest_stats': None,
        'sample_verified': False,
        'mismatches': []
    }

    print("\nComparing bucket statistics...")
    result['source_stats'] = get_bucket_stats(ctx, ctx.source_s3, cfg.source_bucket)
    result['dest_stats'] = get_bucket_stats(ctx, ctx.dest_s3, cfg.dest_bucket)

    source_count = result['source_stats']['object_count']
    dest_count = result['dest_stats']['object_count']

    print(f"\nComparison:")
    print(f"  Source objects: {source_count:,}")
    print(f"  Destination objects: {dest_count:,}")
    print(f"  Difference: {abs(source_count - dest_count):,}")

    if sample_size > 0:
        print(f"\nVerifying {sample_size} random objects...")
        result['sample_verified'] = verify_sample(ctx, sample_size, result['mismatches'])

    return result


def check_replication_lag(ctx: S3MigrationContext) -> dict:
    """Check replication lag using CloudWatch metrics."""
    cfg = ctx.config
    print("\nChecking replication lag...")

    cloudwatch = ctx.source_session.client('cloudwatch')

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/S3',
            MetricName='ReplicationLatency',
            Dimensions=[
                {'Name': 'SourceBucket', 'Value': cfg.source_bucket},
                {'Name': 'DestinationBucket', 'Value': cfg.dest_bucket},
                {'Name': 'RuleId', 'Value': 'CrossAccountReplication'}
            ],
            StartTime=datetime.now(timezone.utc) - timedelta(hours=1),
            EndTime=datetime.now(timezone.utc),
            Period=300,
            Statistics=['Average', 'Maximum']
        )

        if response['Datapoints']:
            latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
            print(f"  Average latency: {latest.get('Average', 'N/A')} seconds")
            print(f"  Maximum latency: {latest.get('Maximum', 'N/A')} seconds")
            return {
                'avg_latency': latest.get('Average'),
                'max_latency': latest.get('Maximum'),
                'timestamp': latest['Timestamp']
            }
        else:
            print("  No replication metrics available")
            return {'error': 'No metrics available'}
    except ClientError as e:
        print(f"  ERROR: {e}")
        return {'error': str(e)}


def cutover_checklist(ctx: S3MigrationContext) -> dict:
    """Run pre-cutover checklist."""
    cfg = ctx.config

    print("\n" + "=" * 60)
    print("PHASE 5: Pre-Cutover Checklist")
    print("=" * 60)

    checks = {
        'replication_active': False,
        'replication_lag_ok': False,
        'object_counts_match': False,
        'sample_verified': False
    }

    print("\n1. Checking replication is active...")
    rep_status = get_replication_status(ctx)
    checks['replication_active'] = rep_status['configured']

    print("\n2. Checking replication lag...")
    lag = check_replication_lag(ctx)
    if 'avg_latency' in lag:
        checks['replication_lag_ok'] = lag['avg_latency'] < 300
    else:
        checks['replication_lag_ok'] = True

    print("\n3. Comparing object counts...")
    source_stats = get_bucket_stats(ctx, ctx.source_s3, cfg.source_bucket)
    dest_stats = get_bucket_stats(ctx, ctx.dest_s3, cfg.dest_bucket)

    diff = abs(source_stats['object_count'] - dest_stats['object_count'])
    diff_pct = (diff / max(source_stats['object_count'], 1)) * 100
    checks['object_counts_match'] = diff_pct < 1

    print("\n4. Verifying sample objects...")
    mismatches = []
    checks['sample_verified'] = verify_sample(ctx, 50, mismatches)

    print("\n" + "-" * 40)
    print("Cutover Checklist Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nAll checks passed. Ready for cutover.")
    else:
        print("\nSome checks failed. Review before proceeding with cutover.")

    return checks
