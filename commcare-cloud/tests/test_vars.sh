#!/usr/bin/env bash
possible_envs=$(commcare-cloud -h | head -n2 | tail -n1 | cut -d'{' -f2 | cut -d'}' -f1 | sed 's/,/ /g')
status_code=0
for env in ${possible_envs}
do
    echo ${env}
    commcare-cloud ${env} _checkvars || status_code=$?
done
exit ${status_code}
