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

COMMCARE_CLOUD_ROOT=$(dirname $(dirname $(readlink -f $0)))
CLUSTER_ENVIRONMENTS=$COMMCARE_CLOUD_ROOT/quick_cluster_install/environments

DEFAULT_ENV="cluster"
DEFAULT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
DEFAULT_SPEC="quick_cluster_install/environments/${DEFAULT_ENV}/spec.yml"

ENV=${ENV:-$DEFAULT_ENV}
BRANCH=${BRANCH:-$DEFAULT_BRANCH}
SPEC=$COMMCARE_CLOUD_ROOT/${SPEC:-$DEFAULT_SPEC}

ENVIRONMENT_DIR=$CLUSTER_ENVIRONMENTS/$ENV

export COMMCARE_CLOUD_ENVIRONMENTS=$CLUSTER_ENVIRONMENTS

confirm_cluster_details() {
  echo ""
  echo "You are about to provision a commcare cluster environment with the following details:"
  echo ""
  echo "Environments directory: ${COMMCARE_CLOUD_ENVIRONMENTS}"
  echo "Environment: ${ENV}"
  echo "Spec file: ${SPEC}"
  echo "Branch: ${BRANCH}"
  echo ""
  echo "Continue? [y/n]"
  read continue

  if [ "$continue" != "y" ] ; then
    echo "We're done here!"
    exit 0
  fi
}

encrypt_vault() {
  ansible-vault encrypt $ENVIRONMENT_DIR/vault.yml
}

sync_to_git() {
  # Check if there's new changes
  if [[ `git status --porcelain` ]]; then
      git add .
      git commit -m "Update ${ENV} files"
      git push origin $BRANCH

      if [ $? -ne 0 ] ; then
        echo "Push to git failed"
        exit 1
      fi
  fi
}

# Provision and create environment files
confirm_cluster_details $1
python $COMMCARE_CLOUD_ROOT/commcare-cloud-bootstrap/commcare_cloud_bootstrap.py provision $SPEC --env $ENV

encrypt_vault $1
sync_to_git $1

echo "Set up commcare-cloud on control machine? [y/n]"
read setup_cc_cloud

if [ "$setup_cc_cloud" != "y" ] ; then
  echo "Cheers!"
  exit 0
fi

INVENTORY_FILE=$ENVIRONMENT_DIR/inventory.ini
SSH_KEY=~/.ssh/commcarehq_cluster_testing.pem

ansible-playbook $COMMCARE_CLOUD_ROOT/quick_cluster_install/install_cluster.yml -i $INVENTORY_FILE --extra-vars "control_host=${ENV}-control-0 git_branch=${BRANCH}" --private-key $SSH_KEY
