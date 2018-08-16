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

echo "(PV): 0"
commcare-cloud $ENV bootstrap-users --quiet --branch=$BRANCH
echo "(PV): 1"
commcare-cloud $ENV ansible-playbook update_apt_cache.yml $PLAYBOOK_TAGS
echo "(PV): 2"
commcare-cloud $ENV ansible-playbook deploy_common.yml $PLAYBOOK_TAGS
echo "(PV): 3"
commcare-cloud $ENV ansible-playbook deploy_lvm.yml $PLAYBOOK_TAGS
# (PV) 1
echo "(PV): 4"
commcare-cloud $ENV ansible-playbook deploy_db.yml $PLAYBOOK_TAGS
#=-=-=-=-=-=-=-=-=-=-=
echo "(PV): 5"
commcare-cloud $ENV ansible-playbook deploy_riakcs.yml $PLAYBOOK_TAGS --skip-tags=delete_riak_secret
echo "(PV): 5.1"
cchq pvtest update-riak
#=-=-=-=-=-=-=-=-=-=-=
echo "(PV): 5.15"
#This clears the file on the riakcs host machine.
commcare-cloud $ENV ansible-playbook deploy_riakcs.yml $PLAYBOOK_TAGS --tags=delete_riak_secret
#=-=-=-=-=-=-=-=-=-=-=
echo "(PV): 5.2"
commcare-cloud $ENV ansible-playbook disable_thp.yml $PLAYBOOK_TAGS
#=-=-=-=-=-=-=-=-=-=-=
echo "(PV): 6"
commcare-cloud $ENV ansible-playbook deploy_commcarehq.yml $PLAYBOOK_TAGS
echo "(PV): 7"
commcare-cloud $ENV ansible-playbook deploy_proxy.yml $PLAYBOOK_TAGS
echo "(PV): 8"
commcare-cloud $ENV ansible-playbook deploy_shared_dir.yml $PLAYBOOK_TAGS
echo "(PV): 9"
commcare-cloud $ENV ansible-playbook deploy_webworker.yml $PLAYBOOK_TAGS
echo "(PV): 10"
commcare-cloud $ENV ansible-playbook deploy_formplayer.yml $PLAYBOOK_TAGS
echo "(PV): 11"
commcare-cloud $ENV ansible-playbook deploy_mailrelay.yml $PLAYBOOK_TAGS
echo "(PV): 12"
commcare-cloud $ENV ansible-playbook deploy_tmpreaper.yml $PLAYBOOK_TAGS
echo "(PV): 13"
commcare-cloud $ENV ansible-playbook deploy_etckeeper.yml $PLAYBOOK_TAGS
echo "(PV): 14"
commcare-cloud $ENV ansible-playbook deploy_airflow.yml $PLAYBOOK_TAGS
# migrate must happen before first fab, and also before touchforms can create its special user
echo "(PV): 15"

commcare-cloud $ENV ansible-playbook migrate_on_fresh_install.yml $PLAYBOOK_TAGS
echo "(PV): 16"
commcare-cloud $ENV ansible-playbook deploy_touchforms.yml $PLAYBOOK_TAGS
echo "(PV): 17"
commcare-cloud $ENV ansible-playbook deploy_http_proxy.yml $PLAYBOOK_TAGS
echo "(PV): 18"
commcare-cloud $ENV fab deploy:confirm=no,skip_record=yes --show=debug --set ignore_kafka_checkpoint_warning=true --branch=$BRANCH
echo "(PV): 19"
commcare-cloud $ENV django-manage check_services
echo "(PV): 20"
proxy=$(grep -A1 "\[$ENV-proxy-0\]" environments/$ENV/inventory.ini | tail -n 1| awk '{print $2}' | awk -F'=' '{print $2}')
curl https://${proxy}/serverup.txt --insecure

