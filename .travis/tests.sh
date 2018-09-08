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
        # Eventually here we will run something like
        #   git clone https://github.com/dimagi/commcare-environments.git
        # to get the environments (once environments/ is removed from this repo).
        ln -s environments commcare-environments
        COMMCARE_CLOUD_ENVIRONMENTS=commcare-environments manage-commcare-cloud test-environments
    }

    test_autogen_docs() {
        ./tests/test_autogen_docs.sh
    }

    test_syntax
    test_localsettings
    test_dimagi_environments
    nosetests -v
    test_autogen_docs

elif [[ ${TEST} = 'prove-deploy' ]]
then
    bootstrap() {
        ssh-keygen -f ~/.ssh/id_rsa -N "" -q
        cp ~/.ssh/id_rsa.pub .travis/environments/_authorized_keys/travis.pub
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments bash commcare-cloud-bootstrap/bootstrap.sh hq-${TRAVIS_COMMIT} FETCH_HEAD .travis/spec.yml
    }
    bootstrap
fi
