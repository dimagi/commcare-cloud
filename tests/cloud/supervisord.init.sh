#!/bin/bash
#
# Source: https://gist.github.com/betapcode/0215d18481af470b21d26e978f3a0201
# Also tried https://github.com/Supervisor/initscripts/blob/main/ubuntu
# but that one did not work well with supervisor 4.0.4. We may want to revisit
# this when upgrading beyond Ubuntu 18.04
#
# supervisord   Startup script for the Supervisor process control system
#
#       AUTHOR :  betapcode - betapcode@gmail.com
#       COMPANY:  Tamtay JSC
#       VERSION:  1.0
#       CREATED:  04/11/2016 10:31:01 AM
#
# chkconfig:    345 83 04
# description: Supervisor is a client/server system that allows \
#   its users to monitor and control a number of processes on \
#   UNIX-like operating systems.

### BEGIN INIT INFO
# Provides: supervisord
# Required-Start: $all
# Required-Stop: $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: start and stop Supervisor process control system
# Description: Supervisor is a client/server system that allows
#   its users to monitor and control a number of processes on
#   UNIX-like operating systems.
### END INIT INFO

# Source system settings
if [ -f /etc/sysconfig/supervisord ]; then
    . /etc/sysconfig/supervisord
fi

# Path to the supervisorctl script, server binary,
# and short-form for messages.
supervisorctl=/usr/local/bin/supervisorctl
supervisord=${SUPERVISORD-/usr/local/bin/supervisord}
prog=supervisord
pidfile=${PIDFILE-/var/run/supervisord.pid}
lockfile=${LOCKFILE-/var/lock/subsys/supervisord}
STOP_TIMEOUT=${STOP_TIMEOUT-60}
OPTIONS="${OPTIONS--c /etc/supervisord.conf}"
RETVAL=0

start() {
    echo -n $"Starting $prog: "
    $supervisord $OPTIONS
    RETVAL=$?
    echo
    if [ $RETVAL -eq 0 ]; then
        touch ${lockfile}
        $supervisorctl $OPTIONS status
    fi
    return $RETVAL
}

stop() {
    echo -n $"Stopping $prog: "
    $supervisorctl shutdown
    RETVAL=$?
    echo
    [ $RETVAL -eq 0 ] && rm -rf ${lockfile} ${pidfile}
}

reload() {
    echo -n $"Reloading $prog: "
    LSB=1 killproc -p $pidfile $supervisord -HUP
    RETVAL=$?
    echo
    if [ $RETVAL -eq 7 ]; then
        failure $"$prog reload"
    else
        $supervisorctl $OPTIONS status
    fi
}

restart() {
    stop
    start
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
	      $supervisorctl status
	      ;;
    restart)
        restart
        ;;
    condrestart|try-restart)
        if status -p ${pidfile} $supervisord >&/dev/null; then
          stop
          start
        fi
        ;;
    force-reload|reload)
        reload
        ;;
    *)
        echo $"Usage: $prog {start|stop|restart|condrestart|try-restart|force-reload|reload}"
        RETVAL=2
esac

exit $RETVAL
