#!/bin/bash
### Set initial time of file
if [ ! -f /var/log/login_audit.log ];
   then
LTIME=`stat -c %Y /var/log/auth.log.1`
fi
sleep 60
ATIME=`stat -c %Y /var/log/auth.log.1`
if [ "$ATIME" != "$LTIME" ];
   then    
   /usr/local/sbin/intruder.sh >> /var/log/login_audit.log
   /usr/local/sbin/sudo-report.sh >> /var/log/sudo_audit.log
   LTIME=$ATIME
fi
