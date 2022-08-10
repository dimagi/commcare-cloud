#!/usr/bin/env bash
set -e

COMMCARE_CLOUD_ROOT=$(dirname $(dirname $(readlink -f $0)))
CLUSTER_ENVIRONMENTS_DIR=$COMMCARE_CLOUD_ROOT/quick_cluster_install/environments

ENV=$1
ENVIRONMENT_DIR=$CLUSTER_ENVIRONMENTS_DIR/$ENV

SPEC=$ENVIRONMENT_DIR/spec.yml
RESERVED_GIT_BRANCH="automated-cluster-setup"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
SAMPLE_ENV="sample_environment"

# Set commcare-cloud's environments directory
export COMMCARE_CLOUD_ENVIRONMENTS=$CLUSTER_ENVIRONMENTS_DIR

check_environment() {

#  if [ "${BRANCH}" == "${RESERVED_GIT_BRANCH}" ] ; then
#    echo "Please use another branch"
#    exit 1
#  fi

  if [ "${ENV}" == "${SAMPLE_ENV}" ] ; then
    echo "Please specify a different environment"
    exit 1
  fi

  if [ ! -d $ENVIRONMENT_DIR ] ; then
    echo "Should I create environment '${ENV}' at ${ENVIRONMENT_DIR}? [y/n]"
    read create_env

    if [ "${create_env}" != "y" ] ; then
      echo "No action"
      exit 0
    fi

    cp -r $COMMCARE_CLOUD_ENVIRONMENTS/$SAMPLE_ENV $ENVIRONMENT_DIR

    echo "Created environment '${ENV}' at ${ENVIRONMENT_DIR}"
    echo ""
  fi

  if [ ! -f $SPEC ] ; then
    echo "No specifications file found!"
    exit 1
  fi

  KNOWN_HOSTS_FILE=$ENVIRONMENT_DIR/known_hosts

  if [ ! -f $KNOWN_HOSTS_FILE ] ; then
    touch $KNOWN_HOSTS_FILE
  fi
}

copy_install_config() {
  INSTALL_CONFIG_FILE_ORIGIN=$COMMCARE_CLOUD_ROOT/quick_cluster_install/$ENV.yml
  INSTALL_CONFIG_FILE_DESTINATION=$ENVIRONMENT_DIR/install-config.yml

  if [ ! -f $INSTALL_CONFIG_FILE_ORIGIN ] ; then
    echo "${INSTALL_CONFIG_FILE_ORIGIN} not found!"
    echo "Site host (e.g. example.com):"
    read SITE_HOST

    echo "Server host name (used to set server's email address):"
    read SERVER_HOST_NAME

    echo "Your username to use on the server:"
    read SSH_USERNAME

    echo "Your SSH public key's path (leave blank for default ~/.ssh/id_rsa.pub):"
    read SSH_PUBLIC_KEY

    if [ -z $SSH_PUBLIC_KEY ] ; then
      SSH_PUBLIC_KEY=~/.ssh/id_rsa.pub
    fi

    echo "site_host: ${SITE_HOST}" >> $INSTALL_CONFIG_FILE_ORIGIN
    echo "server_host_name: ${SERVER_HOST_NAME}" >> $INSTALL_CONFIG_FILE_ORIGIN
    echo "ssh_public_key: ${SSH_PUBLIC_KEY}" >> $INSTALL_CONFIG_FILE_ORIGIN
    echo "ssh_username: ${SSH_USERNAME}" >> $INSTALL_CONFIG_FILE_ORIGIN
  fi

  cp $INSTALL_CONFIG_FILE_ORIGIN $INSTALL_CONFIG_FILE_DESTINATION
  echo "env_name: ${ENV}" >> $INSTALL_CONFIG_FILE_DESTINATION
  echo "deploy_branch: ${BRANCH}" >> $INSTALL_CONFIG_FILE_DESTINATION
}

encrypt_vault() {
  echo ""
  echo "Encrypting your environment's passwords file using ansible-vault."
  echo "Please store this password safely as it will be asked multiple times during the install.\n"
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
copy_install_config $1

## Provision and create environment files
python $COMMCARE_CLOUD_ROOT/commcare-cloud-bootstrap/commcare_cloud_bootstrap.py provision $SPEC --env $ENV

CONTROL_HOST="${ENV}-control-0"
CONTROL_IP=$(cchq $ENV lookup control)

encrypt_vault $1
sync_to_git $1

INVENTORY_FILE=$ENVIRONMENT_DIR/inventory.ini
AWS_PEM_FILE=$(grep "pem" "${SPEC}" | grep -o -P '(?<=pem: ).*')

ansible-playbook $COMMCARE_CLOUD_ROOT/quick_cluster_install/ansible-playbooks/prepare-control-machine.yml -i $INVENTORY_FILE --extra-vars "control_host=${CONTROL_HOST} git_branch=${BRANCH} pem_file_path=${AWS_PEM_FILE}" --private-key $AWS_PEM_FILE

echo ""
echo ""
echo "All done! You can now SSH into the control machine:"
echo "ssh -i ${AWS_PEM_FILE} ubuntu@${CONTROL_IP}"
echo ""
