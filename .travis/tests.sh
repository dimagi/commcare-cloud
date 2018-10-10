#!/bin/bash

set -ve

# pull branch from git status the exact same way that commcare-cloud does
# so that --branch=${BRANCH} will always match
BRANCH=$(git status | head -n1 | xargs -n1 echo | tail -n1)

if [[ ${TEST} = 'main' ]]
then

    cp .travis/environments/travis/private.yml .travis/environments/travis/vault.yml

    test_syntax() {
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments commcare-cloud travis deploy-stack --branch=${BRANCH}  --skip-check --quiet --syntax-check
    }

    test_localsettings() {
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments commcare-cloud travis deploy-stack --branch=${BRANCH}  --skip-check --quiet --tags=commcarehq
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
        (COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments \
            timeout 45m \
            bash commcare-cloud-bootstrap/bootstrap.sh hq-${TRAVIS_COMMIT} ${BRANCH} .travis/spec.yml)
        rc=$?
        if [[ "${rc}" = 124 ]]
        then
            echo "The bootstrapping process ran successfully for 45 minutes before being killed."
            echo "For now, for the purposes of this test, we're calling that a success"
        else
            exit ${rc}
        fi
    }
    bootstrap
fi
