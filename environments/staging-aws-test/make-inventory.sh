#!/usr/bin/env bash
ENV=$1
cchq ${ENV} aws-list | xargs -n2 echo \
    | awk 'BEGIN { printf "sed " } { printf "-e '\''s/{{ "$2" }}/"$1"/'\'' " } END { printf "environments/'${ENV}'/inventory.ini.j2" }' \
    | bash > environments/${ENV}/inventory.ini
