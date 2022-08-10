#!/usr/bin/env bash
set -e

while getopts "e:b:s:" options; do
  case $options in
    e) ENV="${OPTARG}"
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
DEFAULT_SPEC="spec.yml"

RESERVED_GIT_BRANCH="automated-cluster-setup"
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)


ENV=${ENV:-$DEFAULT_ENV}
ENVIRONMENT_DIR=$CLUSTER_ENVIRONMENTS/$ENV
BRANCH=${GIT_BRANCH}
SPEC=$ENVIRONMENT_DIR/${SPEC:-$DEFAULT_SPEC}


export COMMCARE_CLOUD_ENVIRONMENTS=$CLUSTER_ENVIRONMENTS

check_environment() {

  if [[ $BRANCH == $RESERVED_GIT_BRANCH && $ENV == $DEFAULT_ENV ]] ; then
    echo "Cluster environment cannot be the default '${ENV}' environment"
    echo "Please specify another environment or use a different git branch"
    exit 1
  fi

  if [ ! -d $ENVIRONMENT_DIR ] ; then
    echo "Should I create environment '${ENV}' at ${ENVIRONMENT_DIR}? [y/n]"
    read create_env

    if [ "${create_env}" != "y" ] ; then
      echo "No action"
      exit 0
    fi

    echo ""
    echo "Creating environment '${ENV}' at ${ENVIRONMENT_DIR}"
    echo ""

    cp -r $COMMCARE_CLOUD_ENVIRONMENTS/$DEFAULT_ENV $ENVIRONMENT_DIR
  fi

  if [ ! -f $SPEC ] ; then
    echo "No specifications file found!"
    exit 1
  fi
}

confirm_cluster_details() {
  echo ""
  echo "You are about to provision a commcare cluster environment with the following details:"
  echo ""
  echo "Environment: ${ENVIRONMENT_DIR}"
  echo "Spec file: ${SPEC}"
  echo "Branch: ${BRANCH}"
  echo ""
  echo "Continue? [y/n]"
  read continue

  if [ "$continue" != "y" ] ; then
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

# Verify that environment exits, otherwise prompt to create it
check_environment $1

# Provision and create environment files
confirm_cluster_details $1

python $COMMCARE_CLOUD_ROOT/commcare-cloud-bootstrap/commcare_cloud_bootstrap.py provision $SPEC --env $ENV

encrypt_vault $1
sync_to_git $1

echo ""
echo "Set up commcare-cloud on control machine? [y/n]"
read setup_cc_cloud

if [ "$setup_cc_cloud" != "y" ] ; then
  echo "Cheers!"
  exit 0
fi

INVENTORY_FILE=$ENVIRONMENT_DIR/inventory.ini
SSH_KEY=~/.ssh/commcarehq_cluster_testing.pem

ansible-playbook $COMMCARE_CLOUD_ROOT/quick_cluster_install/install_cluster.yml -i $INVENTORY_FILE --extra-vars "control_host=${ENV}-control-0 git_branch=${BRANCH}" --private-key $SSH_KEY
