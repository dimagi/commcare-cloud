#!/bin/bash
rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    ansible@10.247.164.14:/opt/data/couchdb2/ /opt/data/couchdb2/ \
    --files-from /tmp/couchdb_migration_rsync_file_list/10.247.164.14__files -r $@

rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    ansible@10.247.164.12:/opt/data/couchdb2/ /opt/data/couchdb2/ \
    --files-from /tmp/couchdb_migration_rsync_file_list/10.247.164.12__files -r $@
