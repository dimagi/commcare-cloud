#!/usr/bin/env bash
set -e
ENV=$1
BRANCH=$2
SPEC=$3

#commcare-cloud-bootstrap provision $SPEC --env $ENV
while
    commcare-cloud $ENV factory-ping all 'echo {{ inventory_hostname }}' -u ubuntu --use-pem
    [ $? = 4 ]
do :
done
#
#commcare-cloud $ENV bootstrap-users --quiet --branch=$BRANCH
#commcare-cloud $ENV deploy-stack --skip-check --quiet -e 'CCHQ_IS_FRESH_INSTALL=1' --branch=$BRANCH
#
### This next line is a temp fix to allow supervisor to actually get installed.
#commcare-cloud $ENV update-users --quiet --branch=$BRANCH --skip-check
#commcare-cloud $ENV fab deploy:confirm=no --show=debug --set ignore_kafka_checkpoint_warning=true
