.. role:: raw-html-m2r(raw)
   :format: html


SSL certificate setup for nginx
===============================

CommCare uses `LetsEncrypt <https://letsencrypt.org/>`_ as the default certificate authority to
generate SSL certificates for nginx.

*commcare-cloud* uses a combination of ansible and `certbot <https://certbot.eff.org/about/>`_
to renew our Letsencrypt certificates. Ansible is used to configure the Nginx and certbot.
Afterwards Certbot is used for the certificate automation.

Use of Ansible
^^^^^^^^^^^^^^


* Installation and configuration of Certbot.
* Configure Nginx configuration files.
* Creation of directories used for http-01 challenge.
* Creating links to Certbot's fullchain.pem and privkey.pem files

Use of Certbot
^^^^^^^^^^^^^^


* Getting certificate for the first time.
* Renewal of certificate 1 month before the expiry.
* Moving symlinks to latest certificate and private key.

Monitoring
^^^^^^^^^^

The expiry of certificates is monitored via external monitoring tools such as Datadog
or Pingdom.

----

Procedure to configure SSL for a new environment
------------------------------------------------

:raw-html-m2r:`<small>**Note from author**: I haven't tried this many times in a row and noted/fixed all the kinks,
so there may be something missing here,
but those are the general steps at this point.
It would be lovely to make it so that it happened on the first setup,
but we're not quite there yet.
If there are any errors or gaps, a github issue or pull requests
would be much appreciated.</small>`

1. Set up site without HTTPS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In ``proxy.yml``\ :


* ``fake_ssl_cert: yes``
* ``letsencrypt_cchq_ssl: yes``
* set ``nginx_combined_cert_value`` and ``nginx_key_value`` to ``null``
  (or remove them)

and run full stack deploy

.. code-block:: bash

   commcare-cloud <env> bootstrap-users
   commcare-cloud <env> deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1'
   commcare-cloud <env> deploy commcare --set ignore_kafka_checkpoint_warning=true

Note: if you already have a running site with a previous cert,
you can just skip this step.

2. Request a letsencrypt cert
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run the playbook to request a letsencrypt cert:

.. code-block:: bash

   cchq <env> ansible-playbook letsencrypt_cert.yml --skip-check

3. Update settings to take advantage of new certs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In ``proxy.yml``\ :


* set ``fake_ssl_cert`` to ``no``

and deploy proxy again.

.. code-block:: bash

   cchq <env> ansible-playbook deploy_proxy.yml
