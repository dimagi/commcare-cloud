# Migration configs for migrating from NIC to TCL

The documents in this folder outline the migration process that was used when migrating
the ICDS environment from the NIC datacenter to the TCL datacenter.

Each service where data was migrated has it's own readme. Most of the migrations were
done at the file level using rsync. In order to simplify that process an automation
command was created to perform the necessary steps based on a configuration file.

The [copy-files](https://dimagi.github.io/commcare-cloud/commcare-cloud/commands/#copy-files) documentation
had more information on the command and it's usage. The configuration files for the command are also
contained in this directory and the README files list the actual commands that were run.

## Services migrated
* CouchDB
* RiakCS
* PostgreSQL
* Elasticsearch
* Nginx static sites

## Services not migrated
* RabbitMQ
  * Celery scheduler was stopped and remaining tasks in queues were allowed to process before the migration
* Kafka
  * All pillows were allowed to process to the end of the Kafka logs before the migration
* Redis
  * Since the data in Redis is only a cache it was not necessary to migrate it

## Reference docs

* [Migration tracker](https://docs.google.com/spreadsheets/d/1ATq3y-2bhp6a6IMAiUnyLCK9695QQT1MXTQO1MGEtKY/edit#gid=251109428)
* [Migration notes](https://docs.google.com/document/d/1EwC6agZ-N7_YvEQJ8Fx0RdikjBSjmcDqRP3tqwcWl08/edit)


### Useful commands
* Stop monit
```
$ cchq icds-cas run-shell-command all -b "service monit [stop|start]"
```

* Start / end downtime
```
cchq icds-cas downtime [start|end]
``` 
