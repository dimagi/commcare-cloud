#!/bin/bash
BACKUP_TYPE=$1
DAYS_TO_RETAIN_BACKUPS=$2

TODAY=$(date +"%Y_%m_%d")
pg_dumpall --clean | gzip  > "/opt/data/backups/postgres_$BACKUP_TYPE_$TODAY.db.gz"

# Remove old backups of this backup type
find /opt/data/backups/ -mtime +$DAYS_TO_RETAIN_BACKUPS -name 'postgres_$BACKUP_TYPE_*' -exec rm {} \;
