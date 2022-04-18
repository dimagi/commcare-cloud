User Access Management
======================

Setting up CommCareHQ Server Administrators
-------------------------------------------

It is possible that a team hosting CommCareHQ may have multiple developers managing the server environment. For a developer (referred to as user in rest of this doc) to be able to enter and execute commands on the server using commcare cloud, users have to be added and then configured. Through the lifetime of a project new users might need to be added to the servers and some users may need to be removed. 

This document describes the process of how to set up additional users on the server and how to remove an existing user.

The process to onboard new users as server administrators involves creating an account for the users on all the servers, adding their SSH key to the servers and finally the users setting up their commcare-cloud on their local machine or on a shared server to execute commcare-cloud commands that perform server administration.

Users can be added to the server in one of two ways:

* During installation
* After installation (in steady state)

After the user(s) have been added, the new users need to set up their commcare-cloud. This involves

#. Cloning commcare cloud repo.
#. Installing commcare cloud.
#. Configuring commcare cloud to use the already existing environments folder that is set up during installation.


Adding users during installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is done during the installation. The process is described in the installation documentation in :ref:`cchq-manual-install` and :ref:`quick-install`.


Adding and Removing users in steady state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only users who have access to the servers and the :ref:`environments config directory<reference/1-commcare-cloud/2-configuration:Creating environments directory>` created during the installation can add new users or remove users.

In order for a user to be added (or removed) to all the servers in the environment in steady state, the following steps are required (any user that has already been successfully added can execute this).

#. Add ``<username>.pub`` key to ``environments/_authorized_keys`` folder.
#. Add <username> to the ``present`` section in the admins.yml file in ``environments/_users/admin.yml``.
#. Run ``cchq <env_name> update-users`` to create the newly added users and add their SSH keys to the servers.

To remove a user, add <username> to the ``absent`` section in the admins.yml file in ``environments/_users/admin.yml`` and run the ``update-users`` command.

Running Commands using commcare-cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The new users need to install commcare-cloud and configre commcare-cloud to the the environments config directory to be able to run the commands. Refer to :ref:`commcare-cloud reference <reference/1-commcare-cloud/1-installation:Installation>` to know how to do this.
