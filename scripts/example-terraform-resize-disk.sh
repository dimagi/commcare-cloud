#!/usr/bin/env bash

# bash scripts/example-terraform-resize-disk.sh production couch3:couch4 master

env=$1
hosts=$2
branch=$3

read -sp "Vault Password for '${env}': " vault_password

for host in $(echo ${hosts} | sed 's/:/ /g')
do

    cchq ${env} terraform apply --skip-secrets -target module.server__${host}-${env}.aws_ebs_volume.ebs_volume &&
    ANSIBLE_VAULT_PASSWORD="${vault_password}" cchq ${env} run-shell-command ${host} "reboot" -b && sleep 10 &&
    until cchq production ping ${host}
    do
        sleep 5
    done &&
    ANSIBLE_VAULT_PASSWORD="${vault_password}" cchq ${env} run-shell-command ${host} "resize2fs /dev/nvme1n1" -b &&
    ANSIBLE_VAULT_PASSWORD="${vault_password}" cchq ${env} after-reboot ${host} --branch=${branch} --quiet
done
