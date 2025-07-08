#!/bin/bash

set -ve

python --version

# pull branch from git status the exact same way that commcare-cloud does
# so that --branch=${BRANCH} will always match
BRANCH=$(git status | head -n1 | xargs -n1 echo | tail -n1)

if [[ ${TEST} = 'main' ]]
then

    cp .tests/environments/testenv/private.yml .tests/environments/testenv/vault.yml

    test_syntax() {
        COMMCARE_CLOUD_ENVIRONMENTS=.tests/environments \
        commcare-cloud testenv deploy-stack --branch=${BRANCH}  --skip-check --quiet --syntax-check
    }

    test_localsettings() {
        COMMCARE_CLOUD_ENVIRONMENTS=.tests/environments \
        commcare-cloud testenv deploy-stack --branch=${BRANCH}  --skip-check --quiet --tags=py3,commcarehq
        sudo python -m py_compile /home/cchq/www/testenv/current/localsettings.py
    }

    test_dimagi_environments() {
        # Eventually here we will run something like
        #   git clone https://github.com/dimagi/commcare-environments.git
        # to get the environments (once environments/ is removed from this repo).
        ln -s environments commcare-environments
        COMMCARE_CLOUD_ENVIRONMENTS=commcare-environments manage-commcare-cloud test-environments
        COMMCARE_CLOUD_ENVIRONMENTS=commcare-environments ./tests/test_autogen_environments.sh
    }

    test_syntax
    test_localsettings
    test_dimagi_environments
    nosetests -v
    ./tests/test_autogen_docs.sh
    ./tests/test_requirements.sh
fi
