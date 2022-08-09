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
DEFAULT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
DEFAULT_SPEC="quick_cluster_install/${DEFAULT_ENV}spec.yml"

ENV=${ENV:-$DEFAULT_ENV}
BRANCH=${BRANCH:-DEFAULT_BRANCH}
SPEC=${SPEC:-$DEFAULT_SPEC}

COMMCARE_CLOUD_ROOT=$(dirname $(dirname $(readlink -f $0)))
CLUSTER_ENVIRONMENTS=$COMMCARE_CLOUD_ROOT/quick_cluster_install/environments
ENVIRONMENT_DIR=$CLUSTER_ENVIRONMENTS/$ENV

export COMMCARE_CLOUD_ENVIRONMENTS=$CLUSTER_ENVIRONMENTS

push_to_git() {
  git add .
  git commit -m "Create environment files"
  git push origin $BRANCH

  if [ $? -ne 0 ] ; then
    echo "Push to git failed"
    exit 1
  fi
}

# Provision and create environment files
#python $COMMCARE_CLOUD_ROOT/commcare-cloud-bootstrap/commcare_cloud_bootstrap.py provision $SPEC --env $ENV

ansible-vault encrypt $ENVIRONMENT_DIR/vault.yml

push_to_git $1

printf "\n"
printf "#################################################"
printf "\n Configure control machine \n"
printf "#################################################"
printf "\n"

INVENTORY_FILE=$ENVIRONMENT_DIR/inventory.ini
SSH_KEY=~/.ssh/commcarehq_cluster_testing.pem

ansible-playbook $COMMCARE_CLOUD_ROOT/quick_cluster_install/install_cluster.yml -i $INVENTORY_FILE --extra-vars "control_host=${ENV}-control-0,git_branch=${BRANCH}" --private-key $SSH_KEY
