#!/bin/bash

test_syntax() {
  ansible-playbook -i .travis/environments/travis/inventory.ini ansible/deploy_stack.yml --syntax-check
}

test_localsettings() {
  cp .travis/environments/travis/private.yml .travis/environments/travis/vault.yml
  COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments commcare-cloud travis deploy-stack --tags=commcarehq
  sudo python -m py_compile /home/cchq/www/travis/current/localsettings.py
}

test_syntax
test_localsettings
