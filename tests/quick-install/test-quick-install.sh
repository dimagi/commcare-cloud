#! /bin/bash
set -e

GROUP_VARS=src/commcare_cloud/ansible/group_vars/all.yml
eval PYVER=$(grep python_version: $GROUP_VARS | head -n1 | cut -d' ' -f2)
# Link GitHub Actions-installed python where ansible virtualenv will find it
[ -z $(which python${PYVER}) ] && sudo ln -s /opt/python/${PYVER}/bin/*${PYVER}* /usr/local/bin/
which python${PYVER}
python${PYVER} --version

cd ./quick_monolith_install
bash cchq-install.sh ../tests/quick-install/test-install-config.yml