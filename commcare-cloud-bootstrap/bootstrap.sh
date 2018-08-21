#!/usr/bin/env bash
set -e
ENV=$1
BRANCH=$2
SPEC=$3
PLAYBOOK_TAGS="--skip-check --quiet --branch=$BRANCH -e CCHQ_IS_FRESH_INSTALL=1"

commcare-cloud-bootstrap provision $SPEC --env $ENV
while
    commcare-cloud $ENV ping all --use-factory-auth
    [ $? = 4 ]
do :
done
commcare-cloud $ENV bootstrap-users --quiet --branch=$BRANCH
commcare-cloud $ENV ansible-playbook update_apt_cache.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_common.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_lvm.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_db.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_riakcs.yml $PLAYBOOK_TAGS --skip-tags=delete_riak_secret
cchq $ENV update-riak-secrets
#This clears the file on the riakcs host machine.
commcare-cloud $ENV ansible-playbook deploy_riakcs.yml $PLAYBOOK_TAGS --tags=delete_riak_secret
commcare-cloud $ENV ansible-playbook disable_thp.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_commcarehq.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_proxy.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_shared_dir.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_webworker.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_formplayer.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_mailrelay.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_tmpreaper.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_etckeeper.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_airflow.yml $PLAYBOOK_TAGS
# migrate must happen before first fab, and also before touchforms can create its special user
commcare-cloud $ENV ansible-playbook migrate_on_fresh_install.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_touchforms.yml $PLAYBOOK_TAGS
commcare-cloud $ENV ansible-playbook deploy_http_proxy.yml $PLAYBOOK_TAGS
commcare-cloud $ENV fab deploy:confirm=no,skip_record=yes --show=debug --set ignore_kafka_checkpoint_warning=true --branch=$BRANCH
commcare-cloud $ENV django-manage check_services
proxy=$(grep -A1 "\[$ENV-proxy-0\]" environments/$ENV/inventory.ini | tail -n 1| awk '{print $2}' | awk -F'=' '{print $2}')
curl https://${proxy}/serverup.txt --insecure

