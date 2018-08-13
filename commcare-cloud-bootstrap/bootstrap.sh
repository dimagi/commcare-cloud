#!/usr/bin/env bash
set -e
ENV=$1
BRANCH=$2
SPEC=$3

commcare-cloud-bootstrap provision $SPEC --env $ENV
while
    commcare-cloud $ENV ping all --use-factory-auth
    [ $? = 4 ]
do :
done

commcare-cloud $ENV bootstrap-users --quiet --branch=$BRANCH

commcare-cloud $ENV ansible-playbook update_apt_cache.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_common.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_lvm.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_db.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_commcarehq.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_proxy.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_shared_dir.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_webworker.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_formplayer.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_mailrelay.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_tmpreaper.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_etckeeper.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_airflow.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
# migrate must happen before first fab, and also before touchforms can create its special user

commcare-cloud $ENV ansible-playbook migrate_on_fresh_install.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_touchforms.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud $ENV ansible-playbook deploy_http_proxy.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'

commcare-cloud $ENV fab deploy:confirm=no,skip_record=yes --show=debug --set ignore_kafka_checkpoint_warning=true --branch=$BRANCH

commcare-cloud $ENV django-manage check_services

proxy=$(grep -A1 "\[$ENV-proxy-0\]" environments/$ENV/inventory.ini | tail -n 1| awk '{print $2}' | awk -F'=' '{print $2}')
curl https://${proxy}/serverup.txt --insecure
