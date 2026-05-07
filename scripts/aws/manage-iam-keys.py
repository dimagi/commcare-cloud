#!/usr/bin/env python3
"""
Manage AWS IAM access keys for a given user.

Usage:
    ./scripts/aws/manage-iam-keys.py <aws-profile> <iam-user> <subcommand>

Subcommands:
    list                    Output a JSON list of the user's access keys, including last-used info.
    create                  Create a new access key and print its credentials as CSV.
    deactivate <key-id>     Set the key status to Inactive and print the updated key info.
    reactivate <key-id>     Set the key status to Active and print the updated key info.
"""

import argparse
import csv
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

    subparsers.add_parser(
        'create', help='Create a new access key and print its credentials as CSV.'
    )

    deactivate_parser = subparsers.add_parser(
        'deactivate', help='Set the given access key to Inactive.'
    )
    deactivate_parser.add_argument('key_id', help='Access key ID to deactivate.')

    reactivate_parser = subparsers.add_parser(
        'reactivate', help='Set the given access key to Active.'
    )
    reactivate_parser.add_argument('key_id', help='Access key ID to reactivate.')

    args = parser.parse_args()

    session = boto3.session.Session(profile_name=args.aws_profile)
    iam = session.client('iam')

    if args.subcommand == 'list':
        print_json(list_keys(iam, args.iam_user))
    elif args.subcommand == 'create':
        print_keyfile(create_key(iam, args.iam_user))
    elif args.subcommand == 'deactivate':
        print_json(set_key_active(iam, args.iam_user, args.key_id, active=False))
    elif args.subcommand == 'reactivate':
        print_json(set_key_active(iam, args.iam_user, args.key_id, active=True))


def list_keys(iam, iam_user):
    keys = iam.list_access_keys(UserName=iam_user)['AccessKeyMetadata']
    result = []
    for key in keys:
        last_used = iam.get_access_key_last_used(
            AccessKeyId=key['AccessKeyId']
        )['AccessKeyLastUsed']
        result.append(_format_key_info(key, last_used))
    return result


def create_key(iam, iam_user):
    key = iam.create_access_key(UserName=iam_user)['AccessKey']
    return {
        'AccessKeyId': key['AccessKeyId'],
        'SecretAccessKey': key['SecretAccessKey'],
    }


def set_key_active(iam, iam_user, access_key_id, active):
    status = 'Active' if active else 'Inactive'
    iam.update_access_key(UserName=iam_user, AccessKeyId=access_key_id, Status=status)
    return _get_key_info(iam, iam_user, access_key_id)


def _get_key_info(iam, iam_user, access_key_id):
    for key in iam.list_access_keys(UserName=iam_user)['AccessKeyMetadata']:
        if key['AccessKeyId'] == access_key_id:
            last_used = iam.get_access_key_last_used(
                AccessKeyId=access_key_id
            )['AccessKeyLastUsed']
            return _format_key_info(key, last_used)
    raise SystemExit(f"Access key {access_key_id} not found for user {iam_user}.")


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


def print_keyfile(key):
    writer = csv.writer(sys.stdout)
    writer.writerow(['Access key ID', 'Secret access key'])
    writer.writerow([key['AccessKeyId'], key['SecretAccessKey']])


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == '__main__':
    main()
