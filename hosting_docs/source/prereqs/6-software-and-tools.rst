.. _software-requirements:

Software and Tools requirements
===============================

A production grade CommCareHQ instance with all the features available requires good number of third-party software. Below is a list of softwares and tools required to run an instance.

#. Ubuntu 18.04 Server as operating system on all environments.
#. :ref:`prereqs/7-commcare-cloud:CommCare Cloud Deployment Tool` to deploy all the other services.
#. Email and SMS gateways for features related to Email and SMS to work.
#. `sentry.io <https://sentry.io>`_  for error logging. If you would like to self host Sentry using commcare-cloud, see :ref:`sentry-on-prem`.
#. Datadog or Prometheus for monitoring and alerting.
#. Google Maps or Mapbox API keys if you are using features that use these APIs.
