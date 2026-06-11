import time
from datetime import datetime, timezone
from typing import Optional

from botocore.exceptions import ClientError

from .orchestrator import S3MigrationContext


def create_datasync_source_location(ctx: S3MigrationContext) -> Optional[str]:
    """Create DataSync source location (S3 bucket)."""
    cfg = ctx.config
    print(f"\nCreating DataSync source location...")

    datasync_role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.datasync_role_name}"

    try:
        response = ctx.source_datasync.create_location_s3(
            S3BucketArn=f"arn:aws:s3:::{cfg.source_bucket}",
            S3Config={
                'BucketAccessRoleArn': datasync_role_arn
            }
        )
        location_arn = response['LocationArn']
        print(f"  Created source location: {location_arn}")
        return location_arn
    except ClientError as e:
        print(f"  ERROR: {e}")
        return None


def create_datasync_destination_location(ctx: S3MigrationContext) -> Optional[str]:
    """Create DataSync destination location (S3 bucket in different account)."""
    cfg = ctx.config
    print(f"\nCreating DataSync destination location...")

    datasync_role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.datasync_role_name}"

    try:
        response = ctx.source_datasync.create_location_s3(
            S3BucketArn=f"arn:aws:s3:::{cfg.dest_bucket}",
            S3StorageClass='INTELLIGENT_TIERING',
            S3Config={
                'BucketAccessRoleArn': datasync_role_arn
            }
        )
        location_arn = response['LocationArn']
        print(f"  Created destination location: {location_arn}")
        return location_arn
    except ClientError as e:
        print(f"  ERROR: {e}")
        return None


def create_datasync_task(ctx: S3MigrationContext,
                         source_location_arn: str,
                         dest_location_arn: str) -> Optional[str]:
    """Create DataSync task for S3 to S3 transfer."""
    cfg = ctx.config
    print(f"\nCreating DataSync task...")

    try:
        response = ctx.source_datasync.create_task(
            SourceLocationArn=source_location_arn,
            DestinationLocationArn=dest_location_arn,
            Name=f"s3-migration-{cfg.source_bucket}-to-{cfg.dest_bucket}",
            TaskMode='ENHANCED',
            Options={
                'VerifyMode': 'ONLY_FILES_TRANSFERRED',
                'OverwriteMode': 'ALWAYS',
                'PreserveDeletedFiles': 'REMOVE',
                'PreserveDevices': 'NONE',
                'PosixPermissions': 'NONE',
                'Uid': 'NONE',
                'Gid': 'NONE',
                'TaskQueueing': 'ENABLED',
                'TransferMode': 'CHANGED',
                'ObjectTags': 'PRESERVE',
                'LogLevel': 'BASIC',
            },
        )
        task_arn = response['TaskArn']
        print(f"  Created task: {task_arn}")
        return task_arn
    except ClientError as e:
        print(f"  ERROR: {e}")
        return None


def start_datasync_task(ctx: S3MigrationContext, task_arn: str) -> Optional[str]:
    """Start a DataSync task execution."""
    print(f"\nStarting DataSync task execution...")

    try:
        response = ctx.source_datasync.start_task_execution(
            TaskArn=task_arn
        )
        execution_arn = response['TaskExecutionArn']
        print(f"  Started execution: {execution_arn}")
        return execution_arn
    except ClientError as e:
        print(f"  ERROR: {e}")
        return None


def get_datasync_task_status(ctx: S3MigrationContext, execution_arn: str) -> dict:
    """Get status of DataSync task execution."""
    try:
        response = ctx.source_datasync.describe_task_execution(
            TaskExecutionArn=execution_arn
        )

        status = {
            'status': response['Status'],
            'bytes_transferred': response.get('BytesTransferred', 0),
            'bytes_written': response.get('BytesWritten', 0),
            'files_transferred': response.get('FilesTransferred', 0),
            'estimated_bytes': response.get('EstimatedBytesToTransfer', 0),
            'estimated_files': response.get('EstimatedFilesToTransfer', 0),
        }

        if status['estimated_bytes'] > 0:
            status['progress_pct'] = (status['bytes_transferred'] / status['estimated_bytes']) * 100
        else:
            status['progress_pct'] = 0

        return status
    except ClientError as e:
        return {'status': 'ERROR', 'error': str(e)}


def monitor_datasync_task(ctx: S3MigrationContext, execution_arn: str, interval: int = 60):
    """Monitor DataSync task until completion."""
    print(f"\nMonitoring DataSync task execution...")
    print(f"  Execution ARN: {execution_arn}")
    print(f"  Checking every {interval} seconds (Ctrl+C to stop monitoring)...")
    print()

    status = None
    try:
        while True:
            status = get_datasync_task_status(ctx, execution_arn)

            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"[{timestamp}] Status: {status['status']}")

            if status['status'] == 'ERROR' and 'error' in status:
                print(f"  API error: {status['error']}, will retry...")
                time.sleep(interval)
                continue

            if status['status'] not in ['QUEUED', 'LAUNCHING', 'PREPARING', 'TRANSFERRING', 'VERIFYING']:
                print(f"\nTask completed with status: {status['status']}")
                if status['status'] == 'SUCCESS':
                    print(f"  Files transferred: {status['files_transferred']:,}")
                    print(f"  Bytes transferred: {status['bytes_transferred']:,}")
                break

            if status['estimated_bytes'] > 0:
                print(f"  Progress: {status['progress_pct']:.1f}%")
                print(f"  Transferred: {status['bytes_transferred']:,} / {status['estimated_bytes']:,} bytes")
                print(f"  Files: {status['files_transferred']:,} / {status['estimated_files']:,}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n\nMonitoring stopped by user. Task is still running.")
        print(f"  Resume monitoring with the same command and profile arguments.")

    return status


def list_datasync_tasks(ctx: S3MigrationContext) -> list:
    """List all DataSync tasks."""
    print("\nListing DataSync tasks...")

    try:
        tasks = []
        paginator = ctx.source_datasync.get_paginator('list_tasks')
        for page in paginator.paginate():
            tasks.extend(page.get('Tasks', []))

        for task in tasks:
            print(f"  {task['Name']}: {task['Status']}")
            print(f"    ARN: {task['TaskArn']}")

        return tasks
    except ClientError as e:
        print(f"  ERROR: {e}")
        return []
