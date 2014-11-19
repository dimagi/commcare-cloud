#!/bin/bash

# Sync file from salt's localsettings.py.template
# and modify for use in this repository
# Usage:
# bash scripts/sync-localsettings.sh /Users/droberts/dimagi/salt-states


salt_localsettings=$1/cchq/localsettings/localsettings.py.template

ansible_localsettings=ansible/roles/commcarehq/templates/localsettings.salt.py.j2

cat $salt_localsettings |
  sed 's/pillar\[localsettings_key\]/localsettings/g' |
  sed 's/|json/|to_nice_json/g' |
  sed 's/hq_deploy_target/deploy_env/g' > $ansible_localsettings

>> $ansible_localsettings cat <<EOF

# Set to something like "192.168.1.5:8000" (with your IP address).
# See corehq/apps/builds/README.md for more information.
BASE_ADDRESS = '{{ SITE_HOST }}'
EOF

echo "Options used:"
echo

grep -o '{{[^}]*localsettings[^}]*}}' $ansible_localsettings | grep -o '[A-Z][A-Z_][A-Z_]*' | sort | uniq
