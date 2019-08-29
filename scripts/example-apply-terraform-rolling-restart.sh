#!/usr/bin/env bash

# bash scripts/example-terraform-resize-disk.sh production couch3:couch4 master

env=$1
hosts=$2
branch=$3

read -sp "Vault Password for '${env}': " vault_password

for host in $(echo ${hosts} | sed 's/:/ /g')
do
    cchq ${env} terraform apply --skip-secrets -target module.server__${host}-${env}.aws_instance.server &&
    until cchq ${env} ping ${host}
    do
        sleep 5
    done &&
    ANSIBLE_VAULT_PASSWORD="${vault_password}" cchq ${env} after-reboot ${host} --branch=${branch} --quiet
done
