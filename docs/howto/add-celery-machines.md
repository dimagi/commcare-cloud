# Add a new celery machine into existing cluster

## Setup the new node
```
diff environments/<env>/inventory.ini
+ [celeryN]
+ <node ip>

```

```
diff environments/<env>/app_process.yml
+   'celery11':
+    reminder_case_update_queue:
+      pooling: gevent
+      concurrency: <int>
+      num_workers: <int>

```

## Configure

1. Configure Shared Directory

```
commcare-cloud <env> ap deploy_shared_dir.yml --tags=nfs --limit=shared_dir_host

```

2. Register with pgbouncer machines

```
cchq $ENV deploy-stack --tags=pgbouncer_hba --limit postgresql
```

3. Deploy new node

```
commcare-cloud <env> deploy_stack.yml --limit=celeryN
```

## Update Configs

```
commcare-cloud <env> update-config
```

## Deploy code

```
cchq <env> fab deploy
```

## Update supervisor config

```
cchq <env> update-supervisor-confs
```