
Migrate plproxy to new node
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This Migration doesn't require downtime since the databases do not contain any data.


#. Update the new node in env config:

   * Replace the old nodes in ``<env>/postgresql.yml`` with new nodes

#. 
   Run ``cchq <env> deploy-stack --limit=<new nodes>`` on new nodes.

#. 
   Run ``cchq <env> update-config --limit=django_manage``


   * Expect to see changes to django settings for this server

#. Validate on ``django_manage`` machine:

   * Log into ``django_manage machine``\ , switch to ``cchq user``\ , navigate to ``/home/cchq/<env>/current/`` and activate python virtual environment
   * Run ``python manage.py configure_pl_proxy_cluster --create_only`` 
   * Run ``env CCHQ_IS_FRESH_INSTALL=1 python manage.py migrate --database <Django DB alias Name>`` (proxy,proxy_standby)
   * Validate settings

     * ``python manage.py check_services``
     * ``python manage.py check --deploy -t database``

#. Run ``cchq <env> update-config`` (no limit)
#. Restart mobile webworkers

   * ``cchq <env> service commcare restart --limit=mobile_webworkers``

#. Check for errors

   * Load the site in a browser
   * Watch monitoring dashboards for errors
   * Watch Sentry for errors

#. Restart remaining services

   * ``cchq <env> service commcare restart --limit= 'all:!mobile_webworkers'``

#. Check for errors again (see step 7)
#. Cleanup:

   * Remove old plproxy nodes from env config (inventory etc)
