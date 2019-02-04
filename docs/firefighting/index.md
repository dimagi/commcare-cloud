This page summarizes how to do various things related to HQ.
For a more user-friendly guide check out [Cory's brown bag on the topic](http://prezi.com/wedwm-dgqto7/firefighting-hq/).

# HQ Architecture and Machines

![](./hq_architecture.jpg)

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

# Notes

All Datadog links will be specific and private to Dimagi employees.
If datadog releases a feature to share dashboard configurations, we will happily share configurations in this repository.
