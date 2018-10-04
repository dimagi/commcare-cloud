#!/usr/bin/env bash
cchq staging-aws-test aws-list | xargs -n2 echo \
    | awk 'BEGIN { printf "sed " } { printf "-e '\''s/{{ "$2" }}/"$1"/'\'' " } END { printf "environments/staging-aws-test/inventory.ini.j2" }' \
    | bash > environments/staging-aws-test/inventory.ini
