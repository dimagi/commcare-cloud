#!/bin/sh
# Fake supervisorctl. Appends its args to the log and prints what the
# supervisorctl module parses: one formplayer program for `status`, and the
# "<name>: started" line it expects after `restart`.
set -e
echo "$*" >> /var/tmp/supervisorctl.log

case "$1" in
  status)
    echo "commcare-hq-molecule-formsplayer-spring   RUNNING   pid 100, uptime 1:00:00"
    ;;
  restart)
    echo "$2: stopped"
    echo "$2: started"
    ;;
esac
