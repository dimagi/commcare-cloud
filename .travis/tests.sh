#!/bin/bash

if [[ ${TEST} = 'main' ]]
then

    test_syntax() {
        ansible-playbook -i .travis/environments/travis/inventory.ini ansible/deploy_stack.yml --syntax-check
    }

    test_localsettings() {
        cp .travis/environments/travis/private.yml .travis/environments/travis/vault.yml
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments commcare-cloud travis deploy-stack --branch=FETCH_HEAD  --skip-check --quiet --tags=commcarehq
        sudo python -m py_compile /home/cchq/www/travis/current/localsettings.py
    }

    test_help_cache() {
        diff <(ansible -h) commcare-cloud/commcare_cloud/help_cache/ansible.txt
        diff <(ansible-playbook -h) commcare-cloud/commcare_cloud/help_cache/ansible-playbook.txt
    }

    test_syntax
    test_localsettings
    test_help_cache
    nosetests

elif [[ ${TEST} = 'prove-deploy' ]]
then
    bootstrap() {
        ssh-keygen -f ~/.ssh/id_rsa.pub -N "" -q
        cp ~/.ssh/id_rsa.pub .travis/environments/_authorized_keys/travis.pub
        bash commcare-cloud-bootstrap/bootstrap.sh hq-${TRAVIS_COMMIT} FETCH_HEAD .travis/spec.yml
    }
    bootstrap
fi
