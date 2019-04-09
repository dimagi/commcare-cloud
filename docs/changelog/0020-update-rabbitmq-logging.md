# 20. Update RabbitMQ logging configuration

**Date:** 2019-04-05

**Optional per env:** _only required on some environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
This change updates the RabbitMQ logging configuration to change the
log level from `info` to `warning`.

## Details
With the upgrade of Celery to v4 the RabbitMQ connection logs have
increased greatly. The logging configuration is being changed to
prevent the logs from growing beyond 10GB in size.

## Steps to update
1. Stop all CommCare services
```bash
commcare-cloud <env> downtime start
```
2. Update the RabbitMQ logs
```bash
commcare-cloud <env> ap deploy_rabbitmq.yml
```
3. Start all CommCare services
```bash
commcare-cloud <env> downtime end
```
