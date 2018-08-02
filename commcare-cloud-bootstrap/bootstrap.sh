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

echo "(PV): 0"
commcare-cloud $ENV ansible-playbook update_apt_cache.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 1"
commcare-cloud $ENV ansible-playbook deploy_common.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 2"
commcare-cloud $ENV ansible-playbook deploy_lvm.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 3"
commcare-cloud $ENV ansible-playbook deploy_db.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 4"
commcare-cloud $ENV ansible-playbook deploy_commcarehq.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 5"
commcare-cloud $ENV ansible-playbook deploy_proxy.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 6"
commcare-cloud $ENV ansible-playbook deploy_shared_dir.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 7"
commcare-cloud $ENV ansible-playbook deploy_webworker.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 8"
commcare-cloud $ENV ansible-playbook deploy_formplayer.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 9"
commcare-cloud $ENV ansible-playbook deploy_mailrelay.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 10"
commcare-cloud $ENV ansible-playbook deploy_tmpreaper.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 11"
commcare-cloud $ENV ansible-playbook deploy_etckeeper.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 12"
commcare-cloud $ENV ansible-playbook deploy_airflow.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 13"
# migrate must happen before first fab, and also before touchforms can create its special user

commcare-cloud $ENV ansible-playbook migrate_on_fresh_install.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 14"
commcare-cloud $ENV ansible-playbook deploy_touchforms.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 15"
commcare-cloud $ENV ansible-playbook deploy_http_proxy.yml --skip-check --quiet --branch=$BRANCH -e 'CCHQ_IS_FRESH_INSTALL=1'
echo "(PV): 16"

commcare-cloud $ENV fab deploy:confirm=no,skip_record=yes --show=debug --set ignore_kafka_checkpoint_warning=true --branch=pv/parallel-2
