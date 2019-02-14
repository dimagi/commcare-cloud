#!/usr/bin/env bash

bash example-apply-terraform-to-single-server-and-bring-back-up.sh production couch3 master

env=$1
host=$2
branch=$3

read -sp "Vault Password for '${env}': " vault_password

cchq ${env} terraform apply --skip-secrets -target module.server__${host}-${env}.aws_instance.server &&
until cchq production ping ${host}
do
    sleep 5
done &&
ANSIBLE_VAULT_PASSWORD="${vault_password}" cchq ${env} after-reboot ${host} --branch=${branch} --quiet
