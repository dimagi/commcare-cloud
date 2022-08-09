#!/usr/bin/env bash
set -e

while getopts "e:b:s:" options; do
  case $options in
    e) ENV="${OPTARG}"
    ;;
    b) BRANCH="${OPTARG}"
    ;;
    s) SPEC="${OPTARG}"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    exit 1
    ;;
  esac
done

DEFAULT_ENV="cluster"
DEFAULT_BRANCH="master"
DEFAULT_SPEC="quick_cluster_install/spec.yml"

ENV=${ENV:-$DEFAULT_ENV}
BRANCH=${BRANCH:-$DEFAULT_BRANCH}
SPEC=${SPEC:-$DEFAULT_SPEC}

echo "Environment: $ENV"
echo "Branch: $BRANCH"
echo "Spec: $SPEC"

echo ""
echo "Continue? [y/n]"
read continue

if [ "$continue" != "y" ] ; then
  echo "Cheers!"
  exit 0
fi

COMMCARE_CLOUD_ROOT=$(dirname $(dirname $(readlink -f $0)))
CLUSTER_ENVIRONMENTS=$COMMCARE_CLOUD_ROOT/quick_cluster_install/environments

# Set commcare-cloud environments to point to test cluster environments
export COMMCARE_CLOUD_ENVIRONMENTS=$CLUSTER_ENVIRONMENTS

python $COMMCARE_CLOUD_ROOT/commcare-cloud-bootstrap/commcare_cloud_bootstrap.py provision $SPEC --env $ENV

while
    commcare-cloud $ENV ping all --use-factory-auth
    [ $? = 4 ]
do :
done
#
#commcare-cloud $ENV deploy-stack --first-time --quiet -e 'CCHQ_IS_FRESH_INSTALL=1' --branch=$BRANCH
#
#commcare-cloud $ENV deploy commcare --quiet --skip_record --show=debug --set ignore_kafka_checkpoint_warning=true --branch=$BRANCH
#
## Make the test superuser test_superuser@test.com, so the postgres service check passes
#echo -e "123\n123" | cchq $ENV django-manage make_superuser test_superuser@test.com
#proxy=$(grep -A1 "\[$ENV-proxy-0\]" environments/$ENV/inventory.ini | tail -n 1| awk '{print $2}' | awk -F'=' '{print $2}')
#
#commcare-cloud $ENV django-manage check_services
#
#curl https://${proxy}/serverup.txt --insecure