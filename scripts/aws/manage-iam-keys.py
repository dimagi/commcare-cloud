#!/usr/bin/env python3
"""
Manage AWS IAM access keys for a given user.

Usage:
    ./scripts/aws/manage-iam-keys.py <aws-profile> <iam-user> <subcommand>

Subcommands:
    list    Output a JSON list of the user's access keys, including last-used info.
"""

import argparse
import json
import sys
from datetime import datetime

import boto3


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('aws_profile', help='AWS profile name to use for credentials.')
    parser.add_argument('iam_user', help='IAM user whose access keys are managed.')
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    subparsers.add_parser('list', help="List the user's access keys as JSON.")

    args = parser.parse_args()

    session = boto3.session.Session(profile_name=args.aws_profile)
    iam = session.client('iam')

    if args.subcommand == 'list':
        print_json(list_keys(iam, args.iam_user))


def list_keys(iam, iam_user):
    keys = iam.list_access_keys(UserName=iam_user)['AccessKeyMetadata']
    result = []
    for key in keys:
        last_used = iam.get_access_key_last_used(
            AccessKeyId=key['AccessKeyId']
        )['AccessKeyLastUsed']
        result.append(_format_key_info(key, last_used))
    return result


def _format_key_info(key, last_used):
    return {
        'UserName': key['UserName'],
        'AccessKeyId': key['AccessKeyId'],
        'Status': key['Status'],
        'CreateDate': key['CreateDate'],
        'LastUsedDate': last_used.get('LastUsedDate'),
        'LastUsedService': last_used.get('ServiceName'),
        'LastUsedRegion': last_used.get('Region'),
    }


def print_json(data):
    json.dump(data, sys.stdout, indent=2, default=_json_default)
    sys.stdout.write('\n')


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == '__main__':
    main()
