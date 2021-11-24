.. _label_datadog-for-monitoring:

Datadog for monitoring
======================

Datadog is a monotoring tool that has support for variety of applications and is easily extendable which is why in our case it is used for monitoring various system, application metrics and also custom CommCareHQ metrics. You can read more about datadog in their `docs <https://docs.datadoghq.com>`_.

commcare-cloud can setup the requisite datadog integration automatically when you do full stack deploy. You will need to set ``DATADOG_ENABLED`` to ``True`` in your environment's public.yml file and add your account api keys to your vault file.

The default configuration sets up all datadog integrations and there might be a lot of data being generated in your datadog account by your CommCare instance. Individual integrations may be turned on/off by setting relvant vars like ``datadog_integration_postgres`` or ``datadog_integration_redis`` etc in public.yml file.


Recommended dashboards
======================

It is recommended to create relevant dashboards and monitoring alerts to get insights into health of your CommCare instance.

Datadog provides API to import dashboards from one account to another account using JSON files. Below are json files for some of the dashboards we use internally.

- `hq-vitals.json <datadog_dashboards/hq-vitals.json>`_ gives a glance of all components of CommCare
- `mobile-success.json <datadog_dashboards/mobile-success.json>`_ for monitoring success rate of mobile requests to the server
- `postgres-overview.json <datadog_dashboards/postgres-overview.json>`_ for Postgres monitoring
- `celery.json <datadog_dashboards/celery.json>`_ for monitoring bakcground application tasks of celery
- `couchdb.json <datadog_dashboards/couchdb.json>`_ for CouchDB monitoring

You may import them to your own account by running relevant datadog API requests. For example, to import hq-vitals ::

    api_key=<YOUR_DATADOG_API_KEY>
    application_key=<YOUR_DATADOG_APPLICATION_KEY>
    curl -X POST -H "Content-type: application/json" -d @<hq-vitals.json> "https://app.datadoghq.com/api/v1/dashboard?api_key=${api_key}&application_key=${application_key}"
