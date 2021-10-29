Monitoring and Alerting
=======================

Guide on how to setup monitoring, what to monitor, how to monitor.

Real time monitoring is essential to get insights into how the system is performing at a given moment and troubleshoot issues as they arise. Monitoring could also be helpful to forecast resources requirements for future scaling. Alerts can be setup on various monitoring metrics to detect resource limits, anamolies that might cause an issue on your server.

commcare-cloud has support for Datadog and Prometheus.

-------
Datadog
-------

Datadog is a monotoring and alerting tool that has support for variety of applications and is easily extendable which is why in our case it is used for monitoring various system, application metrics and also custom CommCareHQ metrics. You can read more about datadog in their docs

commcare-cloud can setup the requisite datadog integration automatically when you do full stack deploy. You will need to set DATADOG_ENABLED to True in your environment’s public.yml file and add your account api keys to your vault file.

The default configuration sets up all datadog integrations and there might be a lot of data metrics being generated in your datadog account by your CommCare instance. Individual integrations may be turned on/off by setting relvant vars like datadog_integration_postgres or datadog_integration_redis etc in public.yml file.

Below we list down important metrics that you should consider as a minimum monitoring setup. Using these metrics you can create various dashboard views and alerts inside your Datadog project.


CommCare Infrastructure Metrics
-------------------------------

Recommended Dashboards
----------------------

Here are few non-exhaustive preset dashboard views that you can import using Datadog `import dashboard through json <https://docs.datadoghq.com/dashboards/#copy-import-or-export-dashboard-json>`_ functionality.


-  `hq-vitals.json <datadog_dashboards/hq-vitals.json>`__ gives a glance of all components of CommCare
-  `mobile-success.json <datadog_dashboards/mobile-success.json>`__ for monitoring success rate of mobile requests to the server
-  `postgres-overview.json <datadog_dashboards/postgres-overview.json>`__ for Postgres monitoring
-  `celery.json <datadog_dashboards/celery.json>`__ for monitoring bakcground application tasks of celery
-  `couchdb.json <datadog_dashboards/couchdb.json>`__ for CouchDB monitoring


----------
Prometheus
----------

<Todo if required>
