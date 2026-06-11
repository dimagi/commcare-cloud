import json
import time
from typing import Optional

from botocore.exceptions import ClientError

from .orchestrator import S3MigrationContext
from .policies import render_policy


def print_iam_policies(ctx: S3MigrationContext):
    """Print all IAM policies for manual setup."""
    cfg = ctx.config

    role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.replication_role_name}"
    datasync_role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.datasync_role_name}"

    print("\n" + "=" * 60)
    print("IAM POLICIES FOR MANUAL SETUP")
    print("=" * 60)

    print("\n" + "-" * 40)
    print(f"1. REPLICATION ROLE TRUST POLICY (Source Account: {cfg.source_account_id})")
    print(f"   Role Name: {cfg.replication_role_name}")
    print("-" * 40)
    print(json.dumps(render_policy("replication_trust.json"), indent=2))

    print("\n" + "-" * 40)
    print(f"2. REPLICATION ROLE POLICY (Source Account: {cfg.source_account_id})")
    print("-" * 40)
    print(json.dumps(
        render_policy("replication_role.json",
                      source_bucket=cfg.source_bucket,
                      dest_bucket=cfg.dest_bucket),
        indent=2))

    print("\n" + "-" * 40)
    print(f"3. DATASYNC ROLE TRUST POLICY (Source Account: {cfg.source_account_id})")
    print(f"   Role Name: {cfg.datasync_role_name}")
    print("-" * 40)
    print(json.dumps(render_policy("datasync_trust.json"), indent=2))

    print("\n" + "-" * 40)
    print(f"4. DATASYNC ROLE POLICY (Source Account: {cfg.source_account_id})")
    print("-" * 40)
    print(json.dumps(
        render_policy("datasync_role.json",
                      source_bucket=cfg.source_bucket,
                      dest_bucket=cfg.dest_bucket),
        indent=2))

    print("\n" + "-" * 40)
    print(f"5. DESTINATION BUCKET POLICY (Dest Account: {cfg.dest_account_id})")
    print(f"   Bucket: {cfg.dest_bucket}")
    print("-" * 40)
    dest_policy = render_policy("destination_bucket.json",
                                role_arn=role_arn,
                                dest_bucket=cfg.dest_bucket)
    datasync_stmt = render_policy("datasync_bucket_stmt.json",
                                  datasync_role_arn=datasync_role_arn,
                                  dest_bucket=cfg.dest_bucket)
    dest_policy['Statement'].append(datasync_stmt)
    print(json.dumps(dest_policy, indent=2))


def create_replication_role(ctx: S3MigrationContext) -> Optional[str]:
    """Create IAM role for S3 replication in source account."""
    cfg = ctx.config
    print(f"\nCreating replication role '{cfg.replication_role_name}'...")

    trust_policy = render_policy("replication_trust.json")
    role_policy = render_policy("replication_role.json",
                                source_bucket=cfg.source_bucket,
                                dest_bucket=cfg.dest_bucket)

    try:
        response = ctx.source_iam.create_role(
            RoleName=cfg.replication_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for S3 cross-account replication"
        )
        role_arn = response['Role']['Arn']
        print(f"  Created role: {role_arn}")

        ctx.source_iam.put_role_policy(
            RoleName=cfg.replication_role_name,
            PolicyName="S3ReplicationPolicy",
            PolicyDocument=json.dumps(role_policy)
        )
        print(f"  Attached replication policy")

        print(f"  Waiting for role propagation...")
        time.sleep(10)

        return role_arn
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"  Role already exists")
            response = ctx.source_iam.get_role(RoleName=cfg.replication_role_name)
            return response['Role']['Arn']
        print(f"  ERROR: {e}")
        return None


def create_datasync_role(ctx: S3MigrationContext) -> Optional[str]:
    """Create IAM role for DataSync in source account."""
    cfg = ctx.config
    print(f"\nCreating DataSync role '{cfg.datasync_role_name}'...")

    trust_policy = render_policy("datasync_trust.json")
    role_policy = render_policy("datasync_role.json",
                                source_bucket=cfg.source_bucket,
                                dest_bucket=cfg.dest_bucket)

    try:
        response = ctx.source_iam.create_role(
            RoleName=cfg.datasync_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for DataSync S3 to S3 transfer"
        )
        role_arn = response['Role']['Arn']
        print(f"  Created role: {role_arn}")

        ctx.source_iam.put_role_policy(
            RoleName=cfg.datasync_role_name,
            PolicyName="DataSyncS3Policy",
            PolicyDocument=json.dumps(role_policy)
        )
        print(f"  Attached DataSync policy")

        print(f"  Waiting for role propagation...")
        time.sleep(10)

        return role_arn
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"  Role already exists, updating policy...")
            ctx.source_iam.put_role_policy(
                RoleName=cfg.datasync_role_name,
                PolicyName="DataSyncS3Policy",
                PolicyDocument=json.dumps(role_policy)
            )
            response = ctx.source_iam.get_role(RoleName=cfg.datasync_role_name)
            return response['Role']['Arn']
        print(f"  ERROR: {e}")
        return None



def apply_destination_bucket_policy(ctx: S3MigrationContext) -> bool:
    """Apply bucket policy to destination bucket, with option to merge or replace."""
    cfg = ctx.config
    print(f"\nApplying bucket policy to destination bucket...")

    role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.replication_role_name}"
    datasync_role_arn = f"arn:aws:iam::{cfg.source_account_id}:role/{cfg.datasync_role_name}"

    try:
        # Check for existing policy
        existing_policy = None
        try:
            existing = ctx.dest_s3.get_bucket_policy(Bucket=cfg.dest_bucket)
            existing_policy = json.loads(existing['Policy'])
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchBucketPolicy':
                raise

        # Build the statements we need
        dest_policy = render_policy("destination_bucket.json",
                                    role_arn=role_arn,
                                    dest_bucket=cfg.dest_bucket)
        datasync_stmt = render_policy("datasync_bucket_stmt.json",
                                      datasync_role_arn=datasync_role_arn,
                                      dest_bucket=cfg.dest_bucket)
        new_statements = dest_policy['Statement']
        new_statements.append(datasync_stmt)

        if existing_policy:
            existing_statements = existing_policy.get('Statement', [])
            print(f"\n  EXISTING bucket policy ({len(existing_statements)} statements):")
            print(json.dumps(existing_policy, indent=2))

            print(f"\n  NEW statements to add ({len(new_statements)} statements):")
            print(json.dumps(new_statements, indent=2))

            print(f"\n  Options:")
            print(f"    1. APPEND - Add new statements to existing policy")
            print(f"    2. REPLACE - Replace entire policy with new statements only")
            print(f"    3. SKIP - Do not modify bucket policy")
            choice = input("\n  Choose (1/2/3): ").strip()

            if choice == '1':
                new_sids = {s['Sid'] for s in new_statements if 'Sid' in s}
                merged = [s for s in existing_statements if s.get('Sid') not in new_sids]
                merged.extend(new_statements)
                existing_policy['Statement'] = merged
                final_policy = existing_policy
            elif choice == '2':
                final_policy = render_policy("destination_bucket.json",
                                             role_arn=role_arn,
                                             dest_bucket=cfg.dest_bucket)
                final_policy['Statement'].append(
                    render_policy("datasync_bucket_stmt.json",
                                  datasync_role_arn=datasync_role_arn,
                                  dest_bucket=cfg.dest_bucket))
            else:
                print(f"  Skipped bucket policy update.")
                return False
        else:
            print(f"\n  No existing bucket policy found.")
            final_policy = render_policy("destination_bucket.json",
                                         role_arn=role_arn,
                                         dest_bucket=cfg.dest_bucket)
            final_policy['Statement'].append(
                render_policy("datasync_bucket_stmt.json",
                              datasync_role_arn=datasync_role_arn,
                              dest_bucket=cfg.dest_bucket))

        ctx.dest_s3.put_bucket_policy(
            Bucket=cfg.dest_bucket,
            Policy=json.dumps(final_policy)
        )
        print(f"  Applied bucket policy to '{cfg.dest_bucket}'")
        return True
    except ClientError as e:
        print(f"  ERROR: {e}")
        return False
