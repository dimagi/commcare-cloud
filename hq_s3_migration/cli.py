#!/usr/bin/env python3
"""
S3 Cross-Account Migration Tool

Implements hybrid approach for large-scale S3 migrations:
- DataSync for bulk transfer of existing data
- S3 Live Replication for ongoing sync

Designed for 204 TB / 1B+ objects with zero-downtime cutover.
"""

import argparse
import sys

from botocore.exceptions import ClientError

from .config import ACCOUNT_IDS, ACCOUNT_NAMES, MigrationConfig
from .datasync import (create_datasync_destination_location,
                       create_datasync_source_location, create_datasync_task,
                       list_datasync_tasks, monitor_datasync_task,
                       start_datasync_task)
from .iam import (apply_destination_bucket_policy, create_datasync_role,
                  create_replication_role, print_iam_policies)
from .orchestrator import S3MigrationContext
from .replication import enable_live_replication, get_replication_status
from .validation import cutover_checklist, validate_migration


def _check_prerequisites(ctx: S3MigrationContext) -> dict:
    """Check all prerequisites for migration."""
    cfg = ctx.config

    print("\n" + "=" * 60)
    print("PHASE 1: Checking Prerequisites")
    print("=" * 60)

    results = {
        'source_bucket_exists': False,
        'dest_bucket_exists': False,
        'source_versioning': False,
        'dest_versioning': False,
        'source_account_verified': False,
        'dest_account_verified': False,
    }

    print("\nVerifying AWS account access...")
    try:
        source_identity = ctx.source_sts.get_caller_identity()
        results['source_account_verified'] = True
        actual_source_account = source_identity['Account']
        print(f"  Source account: {actual_source_account}")
        if actual_source_account != cfg.source_account_id:
            print(f"  WARNING: Configured source account ID ({cfg.source_account_id}) "
                  f"doesn't match actual ({actual_source_account})")
    except ClientError as e:
        print(f"  ERROR: Cannot access source account: {e}")

    try:
        dest_identity = ctx.dest_sts.get_caller_identity()
        results['dest_account_verified'] = True
        actual_dest_account = dest_identity['Account']
        print(f"  Destination account: {actual_dest_account}")
        if actual_dest_account != cfg.dest_account_id:
            print(f"  WARNING: Configured dest account ID ({cfg.dest_account_id}) "
                  f"doesn't match actual ({actual_dest_account})")
    except ClientError as e:
        print(f"  ERROR: Cannot access destination account: {e}")

    print(f"\nChecking source bucket '{cfg.source_bucket}'...")
    try:
        ctx.source_s3.head_bucket(Bucket=cfg.source_bucket)
        results['source_bucket_exists'] = True
        print(f"  Bucket exists")

        versioning = ctx.source_s3.get_bucket_versioning(Bucket=cfg.source_bucket)
        status = versioning.get('Status', 'Disabled')
        results['source_versioning'] = status == 'Enabled'
        print(f"  Versioning: {status}")
    except ClientError as e:
        print(f"  ERROR: {e}")

    print(f"\nChecking destination bucket '{cfg.dest_bucket}'...")
    try:
        ctx.dest_s3.head_bucket(Bucket=cfg.dest_bucket)
        results['dest_bucket_exists'] = True
        print(f"  Bucket exists")

        versioning = ctx.dest_s3.get_bucket_versioning(Bucket=cfg.dest_bucket)
        status = versioning.get('Status', 'Disabled')
        results['dest_versioning'] = status == 'Enabled'
        print(f"  Versioning: {status}")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"  Bucket does not exist (will be created)")
        else:
            print(f"  ERROR: {e}")

    print("\n" + "-" * 40)
    print("Prerequisites Summary:")
    for key, value in results.items():
        status = "OK" if value else "MISSING"
        print(f"  {key}: {status}")

    return results


def _create_destination_bucket(ctx: S3MigrationContext) -> bool:
    """Create destination bucket with versioning enabled."""
    cfg = ctx.config
    print(f"\nCreating destination bucket '{cfg.dest_bucket}'...")

    try:
        if cfg.region == 'us-east-1':
            ctx.dest_s3.create_bucket(Bucket=cfg.dest_bucket)
        else:
            print(f"  This tool is designed to create buckets in the Staging and Production accounts.")
            return False
        print(f"  Created bucket")

        ctx.dest_s3.put_bucket_versioning(
            Bucket=cfg.dest_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print(f"  Enabled versioning")

        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"  Bucket already exists")
            ctx.dest_s3.put_bucket_versioning(
                Bucket=cfg.dest_bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print(f"  Enabled versioning")
            return True
        print(f"  ERROR: {e}")
        return False


def _enable_source_versioning(ctx: S3MigrationContext) -> bool:
    """Enable versioning on source bucket if not already enabled."""
    cfg = ctx.config
    print(f"\nEnabling versioning on source bucket...")

    try:
        ctx.source_s3.put_bucket_versioning(
            Bucket=cfg.source_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print(f"  Versioning enabled on '{cfg.source_bucket}'")
        return True
    except ClientError as e:
        print(f"  ERROR: {e}")
        return False


def _resolve_account_id(value):
    """Resolve account name alias or validate 12-digit account ID."""
    if value in ACCOUNT_IDS:
        return ACCOUNT_IDS[value]
    if value.isdigit() and len(value) == 12:
        return value
    aliases = ', '.join(ACCOUNT_IDS.keys())
    raise argparse.ArgumentTypeError(
        f"Must be a 12-digit account ID or one of: {aliases}. Got: '{value}'"
    )


def main():
    parser = argparse.ArgumentParser(
        description='S3 Cross-Account Migration Tool (Hybrid: DataSync + Live Replication)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  prepare         Check prerequisites and create destination bucket
  setup-iam       Print IAM policies for manual setup or create them
  enable-replication  Enable S3 live replication
  create-datasync Create DataSync task
  start-datasync  Start DataSync task execution
  monitor-datasync Monitor DataSync task execution
  validate        Validate migration status
  cutover-check   Run pre-cutover checklist
  status          Show current migration status

Examples:
  # Check prerequisites
  python -m hq_s3_migration prepare --source-bucket my-source --dest-bucket my-dest \\
      --source-account 111111111111 --dest-account 222222222222

  # Print IAM policies
  python -m hq_s3_migration setup-iam --source-bucket my-source --dest-bucket my-dest \\
      --source-account 111111111111 --dest-account 222222222222

  # Enable live replication
  python -m hq_s3_migration enable-replication --source-bucket my-source --dest-bucket my-dest \\
      --source-account 111111111111 --dest-account 222222222222

  # Create and start DataSync task
  python -m hq_s3_migration create-datasync --source-bucket my-source --dest-bucket my-dest \\
      --source-account 111111111111 --dest-account 222222222222
        """
    )

    parser.add_argument('command', choices=[
        'prepare', 'setup-iam', 'enable-replication', 'create-datasync',
        'start-datasync', 'monitor-datasync', 'validate', 'cutover-check',
        'status'
    ], help='Command to execute')

    parser.add_argument('--source-profile', default='StagingAdminAccess',
                        help='AWS profile for source account')
    parser.add_argument('--dest-profile', default='BackupAdminAccess',
                        help='AWS profile for destination account')
    parser.add_argument('--source-bucket', default='ap-source-for-replication',
                        help='Source bucket name')
    parser.add_argument('--dest-bucket', default='ap-destination-for-replication',
                        help='Destination bucket name')
    parser.add_argument('--source-account', required=True, type=_resolve_account_id,
                        help=f'Source AWS account ID or alias ({", ".join(ACCOUNT_IDS.keys())})')
    parser.add_argument('--dest-account', required=True, type=_resolve_account_id,
                        help=f'Destination AWS account ID or alias ({", ".join(ACCOUNT_IDS.keys())})')
    parser.add_argument('--region', default='us-east-1',
                        help='AWS region')
    parser.add_argument('--disable-rtc', action='store_true',
                        help='Disable S3 Replication Time Control (enabled by default)')
    parser.add_argument('--create-iam', action='store_true',
                        help='Create IAM roles (for setup-iam command)')
    parser.add_argument('--task-arn',
                        help='DataSync task ARN (for start-datasync)')
    parser.add_argument('--execution-arn',
                        help='DataSync execution ARN (for monitor-datasync)')

    args = parser.parse_args()

    # Append environment name to role names for uniqueness across accounts
    env_name = ACCOUNT_NAMES.get(args.source_account, args.source_account)
    replication_role = f"s3-cross-account-replication-role-{env_name}"
    datasync_role = f"datasync-s3-access-role-{env_name}"

    config = MigrationConfig(
        source_profile=args.source_profile,
        dest_profile=args.dest_profile,
        source_bucket=args.source_bucket,
        dest_bucket=args.dest_bucket,
        source_account_id=args.source_account,
        dest_account_id=args.dest_account,
        region=args.region,
        enable_rtc=not args.disable_rtc,
        replication_role_name=replication_role,
        datasync_role_name=datasync_role,
    )

    ctx = S3MigrationContext(config)

    if args.command == 'prepare':
        results = _check_prerequisites(ctx)
        if not results['source_bucket_exists']:
            print("\nERROR: Source bucket does not exist. Aborting.")
            sys.exit(1)
        if not results['source_account_verified'] or not results['dest_account_verified']:
            print("\nERROR: Cannot verify AWS account access. Aborting.")
            sys.exit(1)
        if not results['dest_bucket_exists']:
            _create_destination_bucket(ctx)
        else:
            if not results['dest_versioning']:
                ctx.dest_s3.put_bucket_versioning(
                    Bucket=config.dest_bucket,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                print(f"\n  Enabled versioning on existing destination bucket")
        _enable_source_versioning(ctx)

    elif args.command == 'setup-iam':
        print_iam_policies(ctx)
        if args.create_iam:
            print("\n" + "=" * 60)
            print("Creating IAM Resources")
            print("=" * 60)
            create_replication_role(ctx)
            create_datasync_role(ctx)
            apply_destination_bucket_policy(ctx)

    elif args.command == 'enable-replication':
        enable_live_replication(ctx)

    elif args.command == 'create-datasync':
        source_loc = create_datasync_source_location(ctx)
        if source_loc:
            dest_loc = create_datasync_destination_location(ctx)
            if dest_loc:
                task_arn = create_datasync_task(ctx, source_loc, dest_loc)
                if task_arn:
                    print(f"\nDataSync task created successfully!")
                    print(f"Task ARN: {task_arn}")
                    print(f"\nTo start the task, run:")
                    print(f"  python -m hq_s3_migration.cli start-datasync --task-arn '{task_arn}' \\")
                    print(f"      --source-profile {args.source_profile} --dest-profile {args.dest_profile} \\")
                    print(f"      --source-account {args.source_account} --dest-account {args.dest_account}")

    elif args.command == 'start-datasync':
        if not args.task_arn:
            print("ERROR: --task-arn is required for start-datasync")
            sys.exit(1)
        execution_arn = start_datasync_task(ctx, args.task_arn)
        if execution_arn:
            print(f"\nTo monitor the task, run:")
            print(f"  python -m hq_s3_migration.cli monitor-datasync --execution-arn '{execution_arn}' \\")
            print(f"      --source-profile {args.source_profile} --dest-profile {args.dest_profile} \\")
            print(f"      --source-account {args.source_account} --dest-account {args.dest_account}")

    elif args.command == 'monitor-datasync':
        if not args.execution_arn:
            print("ERROR: --execution-arn is required for monitor-datasync")
            sys.exit(1)
        monitor_datasync_task(ctx, args.execution_arn)

    elif args.command == 'validate':
        validate_migration(ctx)

    elif args.command == 'cutover-check':
        cutover_checklist(ctx)

    elif args.command == 'status':
        _check_prerequisites(ctx)
        get_replication_status(ctx)
        list_datasync_tasks(ctx)


if __name__ == '__main__':
    main()
