#!/bin/bash

set -ve

if [[ ${TEST} = 'main' ]]
then

    cp .travis/environments/travis/private.yml .travis/environments/travis/vault.yml

    test_syntax() {
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments commcare-cloud travis deploy-stack --branch=FETCH_HEAD  --skip-check --quiet --syntax-check
    }

    test_localsettings() {
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments commcare-cloud travis deploy-stack --branch=FETCH_HEAD  --skip-check --quiet --tags=commcarehq
        sudo python -m py_compile /home/cchq/www/travis/current/localsettings.py
    }

    test_dimagi_environments() {
        git clone git@github.com:dimagi/commcare-environments.git
        ln -s commcare-environments/environments environments
        manage-commcare-cloud test-environments
    }

    test_syntax
    test_localsettings
    test_dimagi_environments
    nosetests -v

elif [[ ${TEST} = 'prove-deploy' ]]
then
    bootstrap() {
        ssh-keygen -f ~/.ssh/id_rsa -N "" -q
        cp ~/.ssh/id_rsa.pub environments/_authorized_keys/travis.pub
        bash commcare-cloud-bootstrap/bootstrap.sh hq-${TRAVIS_COMMIT} FETCH_HEAD .travis/spec.yml
    }
    bootstrap
fi
