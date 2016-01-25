#!/bin/bash

test_syntax() {
  ansible-playbook -i ansible/inventories/test ansible/deploy_stack.yml --syntax-check
}

test_localsettings() {
  mkdir -p /home/cchq/www/dev/current
  ansible-playbook -i ansible/inventories/test ansible/deploy_stack.yml -e '@ansible/vars/dev.yml' --tags=localsettings
  python -m py_compile /home/cchq/www/dev/current/localsettings.py
}

test_syntax
test_localsettings
