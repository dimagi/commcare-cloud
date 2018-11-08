#!/usr/bin/env bash
set -e
ENV=$1
BRANCH=$2
SPEC=$3

commcare-cloud-bootstrap provision blahblahblahlbah $SPEC --env $ENV
while
    commcare-cloud $ENV ping all --use-factory-auth
    [ $? = 4 ]
do :
done

commcare-cloud $ENV deploy-stack --first-time --quiet -e 'CCHQ_IS_FRESH_INSTALL=1' --branch=$BRANCH

commcare-cloud $ENV fab deploy:confirm=no,skip_record=yes --show=debug --set ignore_kafka_checkpoint_warning=true --branch=$BRANCH

# Make the test superuser test_superuser@test.com, so the postgres service check passes
echo -e "123\n123" | cchq $ENV django-manage make_superuser test_superuser@test.com
proxy=$(grep -A1 "\[$ENV-proxy-0\]" environments/$ENV/inventory.ini | tail -n 1| awk '{print $2}' | awk -F'=' '{print $2}')

commcare-cloud $ENV django-manage check_services

curl https://${proxy}/serverup.txt --insecure
