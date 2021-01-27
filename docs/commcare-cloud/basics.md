# Server management basics

## Deploy CommCare HQ
To deploy a new version of CommCare HQ

```
$ commcare-cloud <env> deploy
```

For more detailed deploy details see [Deploy](deploy.md)

## Stop all CommCare HQ services
```
$ commcare-cloud <env> service commcare stop
$ commcare-cloud <env> service commcare start
```

OR

```
$ commcare-cloud <env> downtime start
$ commcare-cloud <env> downtime end
```

In addition to stopping all services this command will
check to see if any processes are still running and give you the
option of terminating them or waiting for them to stop.

## Manage services
To manage services you can use the `service` command
```
$ commcare-cloud <env> service postgresql [status|start|stop|restart]
$ commcare-cloud <env> service --help
```

## Handling a reboot
When a server reboots there are a number of tasks that should be run
to ensure that the encrypted drive is decrypted and all systems are
brought back up.
```
$ commcare-cloud <env> after-reboot --limit <inventory name or IP> all
```

## Update CommCare HQ local settings
To roll out changes to the `localsettings.py` file for Django
or the `application.properties` file for Formplayer:
```
$ commcare-cloud <env> update-config
```

Note that you will need to restart the services in order for the changes
to be picked up by the processes.

## Run Django Management Commands
To run Django management commands we need to log into a machine which has Django configured. Usually we run these commands on the `django_manage` machine which is a `webworker` machine.
```
$ cchq <env> ssh django_manage
$ sudo -iu cchq   #Switch to cchq user
$ cd /home/cchq/www/<env>/current # Change directory to current django release folder
$ source python_env/bin/activate  # Activate the python virtual env
$ ./manage.py <command>  # Run the command
```

There is also an alternate method for running management commands which can be useful in certain situations:

```
$ cchq <env> django-manage <command> <options>
```

Here are some common examples:

```
# get a Django shell
$ cchq <env> django-manage shell

# get a DB shell
$ cchq <env> django-manage dbshell --database <dbalias>

# check services
$ cchq <env> django-manage check-services
```
---

[︎⬅︎ Overview](..)
