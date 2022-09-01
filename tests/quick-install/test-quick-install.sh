#! /bin/bash
set -e

echo 'abc123' >> ~/vault_pass.txt
ANSIBLE_VAULT_PASSWORD_FILE=$(readlink -f ~/vault_pass.txt)

cd ./quick_monolith_install
bash -x cchq-install.sh ../tests/quick-install/test-install-config.yml