import json

from botocore.exceptions import ClientError

from .orchestrator import S3MigrationContext
from .policies import render_policy

RETENTION_SECONDS = "1209600"  # 14 days, SQS max

FAILURE_EVENTS = ["s3:Replication:OperationFailedReplication"]
THRESHOLD_EVENTS = [
    "s3:Replication:OperationMissedThreshold",
    "s3:Replication:OperationReplicatedAfterThreshold",
    "s3:Replication:OperationNotTracked",
]


def _ensure_queue(ctx, queue_name):
    """Create (or look up) a queue; return its URL."""
    try:
        resp = ctx.source_sqs.create_queue(QueueName=queue_name)
        return resp["QueueUrl"]
    except ClientError as e:
        if e.response["Error"]["Code"] in ("QueueNameExists",
                                           "QueueAlreadyExists",
                                           "AWS.SimpleQueueService.QueueNameExists"):
            return ctx.source_sqs.get_queue_url(QueueName=queue_name)["QueueUrl"]
        raise


def _queue_arn(ctx, queue_url):
    resp = ctx.source_sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["QueueArn"]
    )
    return resp["Attributes"]["QueueArn"]


def create_monitoring_queues(ctx: S3MigrationContext) -> dict:
    """Create the failure + threshold SQS queues with retention and access policy."""
    cfg = ctx.config
    print("\n" + "=" * 60)
    print("Creating Replication Monitoring Queues")
    print("=" * 60)

    result = {}
    for key, name in (("failures", cfg.failures_queue_name),
                      ("threshold", cfg.threshold_queue_name)):
        print(f"\nQueue '{name}'...")
        try:
            url = _ensure_queue(ctx, name)
            arn = _queue_arn(ctx, url)

            ctx.source_sqs.set_queue_attributes(
                QueueUrl=url,
                Attributes={"MessageRetentionPeriod": RETENTION_SECONDS},
            )
            policy = render_policy(
                "sqs_queue_access.json",
                queue_arn=arn,
                source_bucket=cfg.source_bucket,
                source_account_id=cfg.source_account_id,
            )
            ctx.source_sqs.set_queue_attributes(
                QueueUrl=url,
                Attributes={"Policy": json.dumps(policy)},
            )
            print(f"  URL: {url}")
            print(f"  ARN: {arn}")
            print(f"  Retention: 14 days; access policy applied")
            result[key] = {"url": url, "arn": arn}
        except ClientError as e:
            print(f"  ERROR: {e}")
            result[key] = None

    return result


def configure_bucket_notifications(ctx: S3MigrationContext,
                                   failure_arn: str,
                                   threshold_arn: str) -> bool:
    """Merge our replication-event queue notifications into the source bucket config."""
    cfg = ctx.config
    print(f"\nConfiguring bucket notifications on '{cfg.source_bucket}'...")

    try:
        existing = ctx.source_s3.get_bucket_notification_configuration(
            Bucket=cfg.source_bucket
        )
    except ClientError as e:
        print(f"  ERROR reading existing notifications: {e}")
        return False

    notif = {k: v for k, v in existing.items() if k != "ResponseMetadata"}

    ours = {
        "replication-failures": {
            "Id": "replication-failures",
            "QueueArn": failure_arn,
            "Events": FAILURE_EVENTS,
        },
        "replication-threshold": {
            "Id": "replication-threshold",
            "QueueArn": threshold_arn,
            "Events": THRESHOLD_EVENTS,
        },
    }

    queue_cfgs = [
        c for c in notif.get("QueueConfigurations", [])
        if c.get("Id") not in ours
    ]
    queue_cfgs.extend(ours.values())
    notif["QueueConfigurations"] = queue_cfgs

    try:
        ctx.source_s3.put_bucket_notification_configuration(
            Bucket=cfg.source_bucket,
            NotificationConfiguration=notif,
        )
        print(f"  Applied notifications (failures + threshold queues)")
        return True
    except ClientError as e:
        print(f"  ERROR: {e}")
        return False


def _queue_exists(ctx, queue_name) -> bool:
    try:
        ctx.source_sqs.get_queue_url(QueueName=queue_name)
        return True
    except ClientError as e:
        if "NonExistentQueue" in e.response["Error"]["Code"]:
            return False
        raise


def get_monitoring_status(ctx: S3MigrationContext) -> dict:
    """Print and return monitoring queue + notification status."""
    cfg = ctx.config
    print("\nChecking replication monitoring status...")

    status = {
        "failures_exists": _queue_exists(ctx, cfg.failures_queue_name),
        "threshold_exists": _queue_exists(ctx, cfg.threshold_queue_name),
        "notifications": [],
    }

    try:
        notif = ctx.source_s3.get_bucket_notification_configuration(
            Bucket=cfg.source_bucket
        )
        status["notifications"] = notif.get("QueueConfigurations", [])
    except ClientError as e:
        print(f"  ERROR reading notifications: {e}")

    print(f"  Failures queue: {'OK' if status['failures_exists'] else 'MISSING'}")
    print(f"  Threshold queue: {'OK' if status['threshold_exists'] else 'MISSING'}")
    print(f"  Bucket queue notifications: {len(status['notifications'])}")
    return status


FILE_ROTATION = 10000


def drain_queue_to_jsonl(ctx: S3MigrationContext,
                         queue_url: str,
                         output_prefix: str,
                         delete: bool = False,
                         max_messages=None) -> tuple:
    """Drain queue messages into JSONL files, 10,000 entries per file.

    Each line is the raw message body (for S3 event notifications, a JSON object).
    Returns (file_paths, total_count). With delete=False (peek) messages are not
    removed and full coverage is NOT guaranteed (visibility timeout + duplicates).
    """
    if not delete:
        print("  WARNING: peek mode (no delete) does not guarantee full coverage "
              "and may return duplicates.")

    file_paths = []
    total = 0
    file_index = 0
    current_file = None
    lines_in_file = 0

    def open_new_file():
        nonlocal file_index, current_file, lines_in_file
        if current_file:
            current_file.close()
        file_index += 1
        path = f"{output_prefix}-{file_index:04d}.jsonl"
        file_paths.append(path)
        current_file = open(path, "w")
        lines_in_file = 0

    open_new_file()

    try:
        while True:
            if max_messages is not None and total >= max_messages:
                break
            resp = ctx.source_sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
            )
            messages = resp.get("Messages", [])
            if not messages:
                break

            handles = []
            for msg in messages:
                if lines_in_file >= FILE_ROTATION:
                    open_new_file()
                current_file.write(msg.get("Body", "") + "\n")
                lines_in_file += 1
                total += 1
                handles.append(msg["ReceiptHandle"])
                if max_messages is not None and total >= max_messages:
                    break

            current_file.flush()

            if delete and handles:
                ctx.source_sqs.delete_message_batch(
                    QueueUrl=queue_url,
                    Entries=[{"Id": str(i), "ReceiptHandle": h}
                             for i, h in enumerate(handles)],
                )
            print(f"  Drained {total} messages into {len(file_paths)} file(s)")
    finally:
        if current_file:
            current_file.close()

    return file_paths, total
