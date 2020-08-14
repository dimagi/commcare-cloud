#!/usr/bin/env python3

# Copy-paste-edited from https://docs.aws.amazon.com/ses/latest/DeveloperGuide/smtp-credentials.html
# Example Usage:
#   CREDENTIAL_FILE=/path/to/downloaded/iam_user_name_accessKeys.csv
#   SES_SECRET=$(cat ${CREDENTIAL_FILE} | head -n2 | tail -n1 | cut -d',' -f2)
#   ./scripts/aws/derive_ses_smtp_password.py --region us-east-1 --secret ${SES_SECRET}

import hmac
import hashlib
import base64
import argparse

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


def main():
    parser = argparse.ArgumentParser(description='Convert a Secret Access Key for an IAM user to an SMTP password.')
    parser.add_argument('--secret',
            help='The Secret Access Key that you want to convert.',
            required=True,
            action="store")
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

    calculateKey(args.secret,args.region)


main()
