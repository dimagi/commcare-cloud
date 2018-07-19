#!/bin/bash
rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    ansible@10.247.164.12:/opt/data/couchdb2/ /opt/data/couchdb2/ \
    --files-from /tmp/file_migration/10.247.164.12_4a7327fd__files -r $@
