.. _go-live-checklist:

Go Live Checklist
=================

There are many things to be set up correctly before your CommCareHQ instance is made accessible over the internet. This checklist helps you to plan a new environment setup and make sure that you have everything ready to go live.

#. Procure necessary compute, storage and any other hardware.
#. Procure licenses or necessary subscriptions if you will be using any external services such as Datadog, Sentry and Email/SMS gateways.
#. Install necessary virtualization software and Ubuntu operation system.
#. Secure the servers where CommCareHQ will be installed.
#. Make sure :ref:`hq-ports` are not blocked by any firewall or networking rules.
#. Install CommCareHQ using :ref:`quick-install` or :ref:`cchq-manual-install`.
#. Make sure SSL is set up and do an application deploy. Both of these are described in the installation docs.
#. Test that your environment is set up correctly by :ref:`new-env-qa`.
#. If you are migrating follow :ref:`migrate-project` or :ref:`migrate-instance` and make sure the migration is successful using the tests described in those guides.
#. Make sure you have backups and monitoring set up correctly.
#. Configure DNS for your host address to your nginx server's public IP to go live.
