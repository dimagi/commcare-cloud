#!/bin/bash
rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    ansible@source_host1:source_dir1 target_dir1 \
    --files-from /tmp/file_migration/source_host1_25b7e83b__files -r $@

rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    ansible@source_host1:source_dir2 target_dir2 \
    --files-from /tmp/file_migration/source_host1_ab2c0d8f__files -r $@

rsync -e 'ssh -oStrictHostKeyChecking=no' --append-verify -aH --info=progress2 \
    ansible@source_host2:source_dir1 target_dir1 \
    --files-from /tmp/file_migration/source_host2_25b7e83b__files -r $@
