#!/usr/bin/env bash
# Example usage:
#   bash scripts/example-apply-terraform-to-single-server-and-bring-back-up.sh production couch3 master

env=$1
hosts=$2
branch=$3

read -rsp "Vault Password for '${env}': " vault_password

targets_args=""
for host in $(echo ${hosts} | sed 's/:/ /g')
do
  targets_args="${targets_args} -target module.server__${host}-${env}.aws_instance.server"
done

cchq ${env} terraform apply --skip-secrets ${targets_args} &&
until cchq production ping ${host}
do
    sleep 5
done &&
ANSIBLE_VAULT_PASSWORD="${vault_password}" cchq ${env} after-reboot ${host} --branch=${branch} --quiet
