# 1. Change celery beat name

**Date:** 2018-08-20

**Optional per env:** No

**Dependant CommCare version:** None

## Change Context
The celery beat name was  inconsistent with the names of the other celery workers, which
broke a function that tried to parse all of the celery names.

## Details

The celery beat name was name in the following pattern: {{ project }}-{{ deploy_env }}-celerybeat. 
It has been changed to: {{ project }}-{{ deploy_env }}-celery_beat.

## Steps to update

1. Stop the beat service

```bash
cchq <env> service celery stop --only beat
```

2. Update the supervisor configs

```bash
cchq <env> update-supervisor-confs
```

3. Start the beat service

```bash
cchq <env> service celery start --only beat
```
