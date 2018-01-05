#!/usr/bin/env bash

pip install pip --upgrade &

pip install -e commcare-cloud &

# to be able to run ansible commands
pip install -r ansible/requirements.txt &

# to be able to run ansible commands
ansible-galaxy install -r ansible/requirements.yml &

# to be able to run fab commands
pip install -r fab/requirements.txt &

wait

./control/check_install.sh
