.. _quick-install:

Quick Install on Single Server
==============================

This is a guide on how to deploy a CommCareHQ instance on a monolith server using an install script. Please refer to :ref:`deploy-commcarehq` guide to decide if this is the right deployment method for you before proceeding.

Prerequisites
-------------

- A single Ubuntu 18.04 64-bit server
- Root user to SSH into the server
- git must be installed on the server. If not, please use https://github.com/git-guides/install-git#debianubuntu to install git

Installation Steps
------------------

SSH into the server with a root or a user with root privileges, and follow the steps below.


1. Download the commcare-cloud repository.

.. code-block:: bash

	git clone https://github.com/dimagi/commcare-cloud

2. Change into the install directory and populate the config file.

.. code-block:: bash

	cd commcare-cloud/quick_monolith_install
	# copy the sample config file
	cp install-config.yml.sample install-config.yml
	# fill the config and save
	vim install-config.yml

3. Run the installation script. (You may be prompted for sudo password)

.. code-block:: bash

	bash cchq-install.sh install-config.yml


Post Installation and Server Administration
-------------------------------------------

Tracking environments directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On successful installation, the script creates an :ref:`environments config directory<reference/1-commcare-cloud/2-configuration:Creating environments directory>` under `~/environments` that stores all of the configuration. We recommend that you track this via a version control system such as git. This way you can track changes, and share the directory with other team members who may need to perform server administration using commcare-cloud.

.. note::

  You do not need to track install-config.yml in git as it's only relevant for this installation.

Running commcare-cloud commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note that to run any commcare-cloud commands after quick-install you need to login to the VM as either the `ssh_username` configured under `install-config.yml` or as the `ansible` user.

If you wish to let other team members run commcare-cloud commands, you can refer to :ref:`reference/3-user-management:User Access Management`.

Once you have installed CommCare HQ successfully you can refer to :ref:`installation/2-manual-install:First Steps with CommCare HQ` before making your CommCare HQ instance live.


Troubleshooting
---------------

The :code:`cchq-install.sh` is an automation of the manual steps listed in :ref:`cchq-manual-install`. If this script fails before it executes :code:`commcare-cloud $env_name deploy-stack --skip-check --skip-tags=users -e 'CCHQ_IS_FRESH_INSTALL=1' -c local --quiet`, you may rerun the script itself. If the script fails at this or latter commands, you can run those commands one after another instead of re-running the enitre `cchq-install.sh` script to save time. Below are the rest of the commands.

To run the commands below, you need to SSH into the machine as the user added earlier or as ansible user.

.. code-block:: bash

	# $env_name is the name of your environment
	commcare-cloud $env_name deploy-stack --skip-check --skip-tags=users -e 'CCHQ_IS_FRESH_INSTALL=1' -c local --quiet
	commcare-cloud $env_name django-manage create_kafka_topics
	commcare-cloud $env_name django-manage preindex_everything
	commcare-cloud $env_name deploy


If you have any issues while deploying please refer to :ref:`troubleshoot-first-time-install`.

