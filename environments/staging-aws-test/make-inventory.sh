#!/usr/bin/env bash
cat <(
    AWS_PROFILE=dimagi aws ec2 describe-instances \
        --filter \
            "Name=tag-key,Values=Name" "Name=tag-value,Values=*$name_tag*" \
            "Name=instance-state-name,Values=running" \
            "Name=tag-key,Values=Environment" "Name=tag-value,Values=staging" \
        --query "Reservations[*].Instances[*][Tags[?Key=='Name'].Value[],NetworkInterfaces[0].PrivateIpAddresses[0].PrivateIpAddress]" \
        --output text --region us-east-1
    ) <(
    AWS_PROFILE=dimagi aws ec2 describe-instances \
        --filter \
            "Name=tag-key,Values=Name" "Name=tag-value,Values=proxy1-staging" \
            "Name=instance-state-name,Values=running" \
        --query "Reservations[*].Instances[*][Tags[?Key=='Name'].Value[],NetworkInterfaces[0].Association.PublicIp]" \
        --output text --region us-east-1 | sed '$s/$/.public_ip/' \
    ) | xargs -n2 echo \
    | awk 'BEGIN { printf "sed " } { printf "-e '\''s/{{ "$2" }}/"$1"/'\'' " } END { printf "environments/staging-aws-test/inventory.ini.j2" }' \
    | bash > environments/staging-aws-test/inventory.ini
