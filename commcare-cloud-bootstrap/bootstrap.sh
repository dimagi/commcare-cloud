#!/usr/bin/env bash
set -e
ENV=$1
BRANCH=$2
SPEC=$3

commcare-cloud-bootstrap provision $SPEC --env $ENV
while
    commcare-cloud $ENV run-shell-command all 'echo {{ inventory_hostname }}' -u ubuntu
    [ $? = 4 ]
do :
done

commcare-cloud $ENV bootstrap-users --quiet --branch=$BRANCH
commcare-cloud $ENV deploy-stack --skip-check --quiet -e 'CCHQ_IS_FRESH_INSTALL=1' --branch=$BRANCH
commcare-cloud $ENV fab deploy:confirm=no
