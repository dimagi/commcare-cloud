#!/bin/bash
rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    \
    ansible@10.162.36.218:/opt/data/ecrypt/couchdb2/ /opt/data/ecrypt/couchdb2/ \
     \
    --files-from /tmp/file_migration/10.162.36.218_6fa4c465__files \
    -r $@ &

    pids[0]=$!


# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done