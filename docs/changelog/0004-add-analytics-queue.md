# 4. Add queue for analytics tasks

**Date:**  2018-08-16

**Optional per env:** Yes

**Dependant CommCare version:** a507757628bc5c087fd1badc0145e39c5bf790ae

## Change Context
Tasks for analytics reporting have been separated into a new analytics celery queue.

## Details
All analytics tasks will be sent to analytics_queue.

## Steps to update
1. Run the following to update the supervisor configuration:

```bash
commcare-cloud <env> update-supervisor-confs
```
