#! /bin/bash
set -e

cd ./quick_monolith_install
# Respond with No to deploy-stack which should be the last step.
echo n | bash cchq-install.sh ../tests/quick-install/test-install-config.yml

# If cchq-install has setup everything successfully, cchq based commands such as below should succeed
test_localsettings() {
    COMMCARE_CLOUD_ENVIRONMENTS=~/environments \
    commcare-cloud testhq deploy-stack  --skip-check --quiet --tags=py3,commcarehq
    sudo python -m py_compile /home/cchq/www/testenv/current/localsettings.py
}

test_localsettings
