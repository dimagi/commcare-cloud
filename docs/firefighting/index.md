This page summarizes how to do various things related to HQ.

# Notes

All Datadog links will be specific and private to Dimagi employees.
If datadog releases a feature to share dashboard configurations, we will happily share configurations in this repository.

For a more user-friendly guide check out [Cory's brown bag on the topic](http://prezi.com/wedwm-dgqto7/firefighting-hq/).

# HQ Architecture and Machines

![](./hq_architecture.png)

# High-level System Monitoring and Alerts

[HQ Vitals](https://app.datadoghq.com/dashboard/g9s-pw6-tpg/hq-vitals?to_ts=1549314000000&is_auto=false&from_ts=1549227600000&live=true&tile_size=m&page=0) - Various graphs on datadog

[Datadog Alerts](https://app.datadoghq.com/monitors/manage?q=status%3A(alert%20OR%20warn%20OR%20"no%20data")) - these are also often reported on #hq-ops or #hq-ops-priority on slack

https://www.commcarehq.org/hq/admin/system/ - catchall system info, contains deploy history, pillowtop info, and a bunch of other stuff

https://www.commcarehq.org/hq/admin/system/check_services - plaintext URL that checks the status of a bunch of support services

# In case of a reboot

## After reboot, whether or not it was deliberate

In case a machine has automatically rebooted or you needed to reboot a machine,
you will need to run the after-reboot protocol directly afterwards.
You can specify a single server by IP address, a single server by its name in inventory.ini.
You will have to confirm to run, and then provide the vault password for your environment.

```bash
$ cchq <env> after-reboot [all|<group>|<server>]
Do you want to apply without running the check first? [y/N]y
```

You don't always control the reboot process (sometimes our provider will expectedly or unexpectedly reboot a VM), but if you do, here's the process end to end:

```bash
# Before shutting down VMs
$ cchq <env> fab supervisorctl:'stop all'
$ cchq <env> ansible-playbook stop_servers.yml

# After restarting VMs
$ cchq <env> after-reboot all
$ cchq <env> fab manage:check_services  # ping various auxiliary services to make sure they're up
  # if any services aren't running, you may have to manually start them:
$ # cchq <env> run-module all service 'name=<service> state=started'
$ cchq <env> fab restart_services  # start app processes
```

# In case of network outage

If there has been a network outage in a cluster (e.g. firewall reboot), the following things should be checked to verify they are working:

## Check services

```bash
$ ./manage.py check_services
# or go to
https://[commcarehq.environment.path]/hq/admin/system/check_services
```

## Check that change feeds are still processing

You can use this graph on [datadog](https://app.datadoghq.com/dashboard/ewu-jyr-udt/change-feeds?to_ts=1549314000000&is_auto=false&live=true&from_ts=1549227600000&tile_size=m&page=0&fullscreen_widget=185100827)

# Service Information

Restarting services: `cchq <env> service <service_name> restart`

Stopping services: `cchq <env> service <service_name> stop`

Service logs: `cchq <env> service <service_name> logs`

## Datadog Dashboards

[postgres/pgbouncer](https://app.datadoghq.com/dash/263336/postgres---overview)

[redis](https://app.datadoghq.com/dash/290868/redis-timeboard)

[rabbitmq](https://app.datadoghq.com/screen/487480/rabbitmq---overview)

[pillow](https://app.datadoghq.com/dash/256236/change-feeds-pillows)

[celery/celerybeat](https://app.datadoghq.com/dash/141098/celery-overview)

[elasticsearch](https://app.datadoghq.com/screen/127236/es-overview)

[kafka](https://app.datadoghq.com/screen/516865/kafka---overview-cloned)

[riak/riak-cs](https://app.datadoghq.com/dash/175518/riak-cs-system-resources)

[couch](https://app.datadoghq.com/screen/177642/couchdb-dashboard)

# Switching to Maintenance Page

To switch to the Maintenance page, if you stop all web workers then the proxy will revert to "CommCareHQ is currently undergoing maintenance...".

```bash
$ cchq <env> fab webworkers supervisorctl:"stop all"
```

To stop all supervisor processes use:

```bash
$ cchq <env> fab supervisorctl:"stop all"
```

# Couch 2.0

## Couch node is down

If a couch node is down, it could mean that it is either very slow at responding to requests or it has stopped running.

Monitors are setup to ping the proxy instead of couch instance directly, so the error will appear as instance:http://<proxy ip>/_node/couchdb_<couch node ip>/

1. log into couch node ip
2. service couchdb2 status
3. If it's not running start it and begin looking through log files (on the proxy, couch's files, maybe kernel or syslog files as well) to see if you can determine the cause of downtime
4. If it is running it could just be very slow at responding.
    a. Use fauxton to see if any tasks are running that could cause couch to become unresponsive (like large indexing tasks)
    b. It could also have ballooned (ICDS) which is out of our control
5. If it's unresponsive and it's out of our control to fix it at the time, go to the proxy machine and comment out the fault node from the nginx config. This will stop sending requests to that server, but it will continue to replicate. When the slowness is over you can uncomment this line and begin proxying reads to it again

## Compacting a shard

If a couch node is coming close to running out of space, it may not have enough space to compact the full db. You can start a compaction of one shard of a database using the following:

`curl "<couch ip>:15986/shards%2F<shard range i.e. 20000000-3fffffff>%2F<database>.<The timestamp on the files of the database>/_compact" -X POST -H "Content-Type: application/json" --user <couch user name>`

It's important to use port 15986. This is the couch node endpoint instead of the cluster. The only way to find the timstamp is to go into /opt/data/couchdb2/shards and look for the filename of the database you want to compact

If it's a global database (like _global_changes), then you may need to compact the entire database at once

`curl "<couch ip>:15984/_global_changes/_compact" -X POST -H "Content-Type: application/json" --user <couch user name>`

# Nginx

Occasionally a staging deploy fails because during a previous deploy, there was an issue uncommenting and re-commenting some lines in the nginx conf.

When this happens, deploy will fail saying

nginx: configuration file /etc/nginx/nginx.conf test failed
To fix, log into the proxy and su as root. Open the config and you'll see something like this

```
/etc/nginx/sites-enabled/staging_commcare
#
# Ansible managed, do not edit directly
#

upstream staging_commcare {
  zone staging_commcare 64k;

    least_conn;

#server hqdjango0-staging.internal-va.commcarehq.org:9010;
#server hqdjango1-staging.internal-va.commcarehq.org:9010;
}
```

Ignore the top warning. Uncomment out the servers. Retsart nginx. Run restart_services.

# NFS & File serving / downloads

For downloading files we let nginx serve the file instead of Django. To do this Django saves the data to a shared NFS drive which is accessible to the proxy server and then returns a response using the XSendfile/X-Accel-Redirect header which tells nginx to look for the file and serve it to the client directly.

The NFS drive is hosted by the DB machine e.g. hqdb0 and is located at /opt/shared_data (see ansible config for exact name). On all the client machines it is located at /mnt/shared_data (again see ansible config for exact name),

## Troubleshooting
### Reconnecting the NFS client

It is possible that the mounted NFS folder on the client machines becomes disconnected from the host in which case you'll see errors like "Webpage not available"

To verify that this is the issue log into the proxy machine and check if there are any files in the shared data directories. If there are folders but no files then that is a good indication that the NFS connections has been lost. To re-establish the connection you should unmount and re-mount the drive:

```bash
$ su
$ umount -l /mnt/shared_data
$ mount /mnt/shared_data
# verify that it is mounted and that there are files in the subfolders
```

### Forcing re-connection of an NFS client in a webworker

It may happen, specially if the client crashes or has kernel oops, that a connection gets in a state where it cannot be broken nor re-established.  This is how we force re-connection in a webworker.
1. Verify NFS is actually stuck
    a. “df” doesn’t work, it hangs. Same goes for lsof.
    b. “umount” results in umount.nfs: /mnt/shared_icds: device is busy
2. top all gunicorns and supervisor
    a. `sudo supervirsorctl stop all`
    b. jVerify “stuck” processes keep running: $ ps aux|grep gunicorn
    c. $ sudo service supervisord stop
    d. Verify “stuck” processes are gone: $ ps aux|grep gunicorn
3. Force umount 
    a. $ sudo umount -f /mnt/shared_icds
4. Re-mount
    a. $ sudo mount /mnt/shared_icds
    b. Verify NFS mount works: $ df
5. Start supervisor and gunicorns
    a. $ sudo service supervisord start
    b. $ sudo supervisorctl start all

If none of the above works check that nfsd is running on the shared_dir_host.

$ ps aux | grep nfsd

$ service nfs-kernel-server status



