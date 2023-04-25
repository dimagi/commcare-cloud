
Migrating Nginx
~~~~~~~~~~~~~~~


#. 
   Install and configure nginx on the new node


   * Add the server in inventory and assign it the ``proxy`` group and ``cas_proxy``\ (For ICDS)
   * Run ``commcare-cloud <env> ap deploy_shared_dir.yml --tags=nfs --limit=shared_dir_host``
   * Run ``commcare-cloud <env> ansible-playbook letsencrypt_cert.yml``
   * Run ``deploy-stack`` for the server.
   * Do a deploy ``cchq <env> deploy``

#. 
   Ensure that any files being served directly by nginx are present and identical to the files on the current node


   * Copy static content from live proxy ``/home/cchq/www/<env>/current/staticfiles`` to new server
   * 
     Copy any other static site content from the live proxy

   * 
     Setup SSL certificates


     * Copy Letsencrypt Configuration dir from live proxy ``/etc/letsencrypt`` to new server

#. 
   QA


   * Do a test if it's working by editing local ``/etc/hosts`` file.

#. 
   Switch traffic to the new proxy.

#. 
   Post steps


   * Replace the old server with the new server in the ``staticfiles`` inventory group.
   * Confirm that the SSL certificate can be renewed correctly by running ``certbot renew --dry-run``
   * Run a code deploy to ensure that the CommCare staticfile process is working correctly with the new proxy.
