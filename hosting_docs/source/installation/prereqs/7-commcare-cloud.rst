CommCare Cloud Deployment Tool
==============================

.. contents:: Table of Contents
    :depth: 2

<Todo: restructure>


Dimagi is proud to be able to share **CommCare Cloud**\ ,
our toolkit for deploying and maintaining CommCare servers,
with our fabulous developer community.

We wrote CommCare Cloud for ourselves,
and it's what we use to manage `CommCare HQ <https://www.commcarehq.org/>`_\ ,
our subscription offering.
Anyone willing to dedicate the considerable amount of effort
and system administration knowledge necessary to stand up and manage a CommCare server
cluster will be able to do so using the same tools that we do.

What is commcare-cloud?
-----------------------

``commcare-cloud`` is a python-based command line tool that uses
the open source technologies Ansible and Fabric to automate everything
you need in order to run a production CommCare cluster.

While it is possible to install on a laptop with a linux-like command line interface,
it is primarily designed to be run on the machine that is hosting CommCare.
(If you are hosting CommCare on more than one machine,
``commcare-cloud`` only needs to be installed on one of them.)
In this documentation, we will call the machine on which ``commcare-cloud`` is installed
the "control machine". If you are hosting CommCare on a single machine,
that machine is also the control machine.

For installation see :ref:`cchq-installation`
For list of available commands see :ref:`cchq-commands`

What is the Control Machine
---------------------------

The machine where ``commcare-cloud`` is installed is known as the control machine. It is a single machine where you will be able to run any service checks, deploy code changes and update CommCare HQ code.

If you are running a `monolith installation <./new_environment.md>`_ this will be the same machine that you installed all the CommCare HQ services on.

We recommend that the control machine be in the same datacenter or network as the rest of your server fleet. 

Setting up a control machine
----------------------------

#. Install ``commcare-cloud`` :ref:`cchq-installation` on it. 
#. Configure ``commcare-cloud`` with `an inventory <../commcare-cloud/env/index.md#inventoryini>`_ of your server fleet. 
#. Update the known-hosts file to access all the servers by running 
   .. code-block:: bash

       $ commcare-cloud <env> update-local-known-hosts

User Management
---------------

User access to all machines on the fleet is managed through the control machine. User permissions are stored in the ``_users`` and ``_authorized_keys`` directories in the environment. 

See more about these files and how to update them in the `environment documentation <../commcare-cloud/env/index.md#_users>`_.

Accessing the control machine
-----------------------------

Once users are correctly added, they should access the control machine with key-forwarding enabled from their own computers. From a Unix machine:

.. code-block:: bash

   $ ssh username@{control_machine IP} -A

If you are a Windows user using PuTTY to access the control machine, follow the instructions on this `SuperUser answer <https://superuser.com/a/878964>`_ to enable key forwarding.

This will allow those users to subsequently ssh into any of the other machines in the fleet, and run any ``commcare-cloud`` commands directly from the control machine.