# Catch any TERM or INT signals and propagate
# to the Celery process. Upon catching of the signal
# the 'wait' command below will terminate and thus will
# exit the bash process.
#
# > When Bash is waiting for an asynchronous command via the wait
# > built-in, the reception of a signal for which a trap has
# > been set will cause the wait built-in to return immediately
# > with an exit status greater than 128, immediately after which
# > the trap is executed.
#
# See Section 12.2.2 of http://tldp.org/LDP/Bash-Beginners-Guide/html/sect_12_02.html
#
# Effectively we've no orphaned
# the Celery process to do a warm shutdown and we are
# free to start another bash process under supervisor.
trap 'kill -TERM $PID' TERM INT
TIMESTAMP=`date +%s`
{{ new_relic_command }}{{ virtualenv_current }}/bin/python {{ code_current }}/manage.py celery worker --queues=celery --events --loglevel=INFO --hostname={{ host_string }}_main.${TIMESTAMP}_timestamp --maxtasksperchild=5 --autoscale={{ celery_params.concurrency }},0 -Ofair &
PID=$!
wait $PID
