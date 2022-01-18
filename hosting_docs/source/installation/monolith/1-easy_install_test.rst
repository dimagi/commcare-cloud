.. _quick-install:

Quick Install on Single Server
==============================

This is a guide on how to deploy a CommCareHQ instance on a monolith server using an install script. Please refer to :ref:`deploy-commcarehq` guide to decide if this is the right deployment method for you before proceeding with this.

Prerequisites
-------------

- A single Ubuntu 18.04 64-bit server
- Root user to SSH into the server
- git must be installed on the server. If not, please use https://github.com/git-guides/install-git#debianubuntu to install git

Installation Steps
------------------

1. Download the commcare-cloud repository.

.. code-block:: bash

	git clone https://github.com/dimagi/commcare-cloud

2. Change into the install directory and fill the config file.

.. code-block:: bash

	cd commcare-cloud/oneclick_monolith_install
	# fill the config and save
	vim install-config.yml

3. Run the installation script.

.. code-block:: bash

	sudo bash cchq-install.sh install-config.yml

.. note::

  You do not need to track install-config.yml under git as it's relevant for this installation only

<Todo/add next steps such as track the env config, code deploy etc>
<Todo/Redirect to next relevent section>
