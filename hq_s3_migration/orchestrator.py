import boto3

from .config import MigrationConfig


class S3MigrationContext:
    """Thin container for boto3 sessions and clients used across migration phases."""

    def __init__(self, config: MigrationConfig):
        self.config = config

        # Initialize boto3 sessions
        self.source_session = boto3.Session(
            profile_name=config.source_profile,
            region_name=config.region
        )
        self.dest_session = boto3.Session(
            profile_name=config.dest_profile,
            region_name=config.region
        )

        # Initialize clients
        self.source_s3 = self.source_session.client('s3')
        self.dest_s3 = self.dest_session.client('s3')
        self.source_iam = self.source_session.client('iam')
        self.dest_iam = self.dest_session.client('iam')
        self.source_datasync = self.source_session.client('datasync')
        self.source_sts = self.source_session.client('sts')
        self.dest_sts = self.dest_session.client('sts')
