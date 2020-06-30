#!/bin/bash
### Set initial time of file
if [ ! -f /var/log/login_audit.log ];
   then
      LTIME=0
   else
      LTIME=`cat /tmp/ATIME`
fi
ATIME=`stat -c %Y /var/log/auth.log.1`
echo $ATIME > /tmp/ATIME
if [ "$ATIME" != "$LTIME" ];
   then    
   /usr/local/sbin/intruder.sh >> /var/log/login_audit.log
   /usr/local/sbin/sudo-report.sh >> /var/log/sudo_audit.log
fi
