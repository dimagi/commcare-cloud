#!/usr/bin/env python3

# Copy-paste-edited from https://docs.aws.amazon.com/ses/latest/DeveloperGuide/smtp-credentials.html
# Example Usage:
#   ./scripts/aws/derive_ses_smtp_password.py --region us-east-1 --csv /path/to/iam_user_name_accessKeys.csv
#   pbpaste | ./scripts/aws/derive_ses_smtp_password.py --region us-east-1 -

import hmac
import hashlib
import base64
import argparse
import csv

# Values that are required to calculate the signature. These values should
# never change.
DATE = "11111111"
SERVICE = "ses"
MESSAGE = "SendRawEmail"
TERMINAL = "aws4_request"
VERSION = 0x04


def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def calculateKey(secretAccessKey, region):
    signature = sign(("AWS4" + secretAccessKey).encode('utf-8'), DATE)
    signature = sign(signature, region)
    signature = sign(signature, SERVICE)
    signature = sign(signature, TERMINAL)
    signature = sign(signature, MESSAGE)
    signatureAndVersion = bytes([VERSION]) + signature
    smtpPassword = base64.b64encode(signatureAndVersion)
    print(smtpPassword.decode('utf-8'))


def extract_secret(content, is_csv):
    if is_csv:
        rows = list(csv.DictReader(content.splitlines()))
        if len(rows) != 1:
            raise ValueError(
                f'Expected exactly one data row in CSV, got {len(rows)}.'
            )
        try:
            return rows[0]['Secret access key']
        except KeyError:
            raise ValueError(
                'CSV is missing a "Secret access key" column. '
                'Expected the AWS access keys download format.'
            )
    return content.strip()


def main():
    parser = argparse.ArgumentParser(description='Convert a Secret Access Key for an IAM user to an SMTP password.')
    parser.add_argument('file',
            type=argparse.FileType('r'),
            help='Path to a file containing the Secret Access Key, or "-" to read from stdin.')
    parser.add_argument('--csv',
            action='store_true',
            help='Interpret the input as the CSV file AWS provides when downloading IAM access keys '
                 '(extracts the "Secret access key" column). Default: input is the secret by itself.')
    parser.add_argument('--region',
            help='The name of the AWS Region that the SMTP password will be used in.',
            required=True,
            choices=[
                'us-east-2',      #US East (Ohio)
                'us-east-1',      #US East (N. Virginia)
                'us-west-2',      #US West (Oregon)
                'ap-south-1',     #Asia Pacific (Mumbai)
                'ap-northeast-2', #Asia Pacific (Seoul)
                'ap-southeast-1', #Asia Pacific (Singapore)
                'ap-southeast-2', #Asia Pacific (Sydney)
                'ap-northeast-1', #Asia Pacific (Tokyo)
                'ca-central-1',   #Canada (Central)
                'eu-central-1',   #Europe (Frankfurt)
                'eu-west-1',      #Europe (Ireland)
                'eu-west-2',      #Europe (London)
                'sa-east-1',      #South America (Sao Paulo)
                'us-gov-west-1'   #AWS GovCloud (US)
            ],
            action="store")
    args = parser.parse_args()

    with args.file as f:
        content = f.read()

    try:
        secret = extract_secret(content, args.csv)
    except ValueError as e:
        parser.error(str(e))

    calculateKey(secret, args.region)


main()
