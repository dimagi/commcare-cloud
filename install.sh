#!/usr/bin/env bash

pip install pip --upgrade
pip install -r requirements.txt
ansible-galaxy install -r ansible/requirements.yml
./control/check_install.sh
