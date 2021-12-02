#!/bin/bash

set -ve

GROUP_VARS=src/commcare_cloud/ansible/group_vars/all.yml
eval PYVER=$(grep python_version: $GROUP_VARS | head -n1 | cut -d' ' -f2)
# Link Travis-installed python where ansible virtualenv will find it
sudo ln -s /opt/python/${PYVER}/bin/*${PYVER}* /usr/local/bin/
which python${PYVER}
python${PYVER} --version

# pull branch from git status the exact same way that commcare-cloud does
# so that --branch=${BRANCH} will always match
BRANCH=$(git status | head -n1 | xargs -n1 echo | tail -n1)

if [[ ${TEST} = 'main' ]]
then

    cp .travis/environments/travis/private.yml .travis/environments/travis/vault.yml

    test_syntax() {
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments \
        commcare-cloud travis deploy-stack --branch=${BRANCH}  --skip-check --quiet --syntax-check
    }

    test_localsettings() {
        COMMCARE_CLOUD_ENVIRONMENTS=.travis/environments \
        commcare-cloud travis deploy-stack --branch=${BRANCH}  --skip-check --quiet --tags=py3,commcarehq
        sudo python -m py_compile /home/cchq/www/travis/current/localsettings.py
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
    ./tests/test_modernize.sh
fi
