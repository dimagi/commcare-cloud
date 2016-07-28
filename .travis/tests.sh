#!/bin/bash

test_syntax() {
  ansible-playbook -i ansible/inventories/test ansible/deploy_stack.yml --syntax-check
}

test_localsettings() {
  ansible-playbook -i ansible/inventories/test ansible/deploy_stack.yml -e '@ansible/vars/dev/dev_private.yml' -e '@ansible/vars/dev/dev_public.yml' --tags=commcarehq
  sudo python -m py_compile /home/cchq/www/dev/current/localsettings.py
}

test_syntax
test_localsettings
