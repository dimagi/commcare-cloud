.. _cchq-installation:

Installation
============

``commcare-cloud`` can be installed on a local machine or on a remote control
machine that's part of the CommCare HQ environment. We recommend installing on a
control machine.

Installation using a script
---------------------------

Step 1.
^^^^^^^

Make sure that you have a non-root user account on the control machine.

Let's say the user is named ``admin`` and the machine
is named ``control.example.com``. Start by logging in as your user via SSH:

.. code-block:: bash

   (laptop)$ ssh admin@control.example.com

(Did that work? Only type the text starting after the ``$`` in these examples.)

You should see a prompt like

.. code-block:: bash

   admin@control.example.com:~$

Step 2. Install uv
^^^^^^^^^^^^^^^^^^

You may skip this step if uv is already installed.

``commcare-cloud`` uses `uv <https://docs.astral.sh/uv/>`_ to manage its Python
environment. See the `uv install docs <https://docs.astral.sh/uv/getting-started/installation/>`_
for your platform. We recommend using ``snap`` on Ubuntu to get a system-wide
installation with automatic updates:

.. code-block:: bash

   sudo snap install astral-uv --classic

Step 3. Install ``commcare-cloud``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Download and run the ``control/init.sh`` script.

.. code-block::

   source <(curl -s https://raw.githubusercontent.com/dimagi/commcare-cloud/master/control/init.sh)

You will see the following prompt

.. code-block::

   Do you want to have the CommCare Cloud environment setup on login?
   (y/n):

If you answer 'y' then a line will be added to your .profile that will
automatically run the init script when you log in, which sets up the
``commcare-cloud`` environment. Otherwise, you can choose to run
``source ~/init-ansible`` manually to setup the environment during future
sessions.

To verify that ``commcare-cloud`` is now installed, run

.. code-block:: bash

   commcare-cloud -h

You should see output like

.. code-block::

   usage: commcare-cloud [-h] [--control] [--control-setup {yes,no}] <env> <command> ...
   ...

...and much more help output describing each command. If you get to this point,
congratulations! ``commcare-cloud`` is installed. You may now use
``commcare-cloud`` or its shorter alias ``cchq`` in any new shell.


Manual Installation
-------------------


First, install ``uv`` (see `Step 2. Install uv`_). Then clone the source code.


.. code-block:: bash

   git clone https://github.com/dimagi/commcare-cloud.git


Option 1: automatic
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   cd commcare-cloud
   source control/init.sh

When prompted:

.. code-block:: bash

   Do you want to have the CommCare Cloud environment setup on login?
   (y/n):

If you answer 'y', a line will be added to your .profile that will automatically
run the init script each time a new shell is launched. Otherwise, you can run
``source ~/init-ansible`` manually to setup the environment as needed during
future sessions.


Option 2: fully manual
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   cd commcare-cloud
   uv sync
   uv run manage-commcare-cloud install

   # (Optional) To use commcare-cloud (cchq) directly without `uv run`
   uv run manage-commcare-cloud configure


If you opted out of the final ``manage-commcare-cloud configure`` step and you
have a local environments directory or cloned the repo somewhere other than
``~/commcare-cloud`` you should set one or both of the following in your bash
profile (\ ``~/.profile``\ ) as needed:

.. code-block:: bash

   # for non-standard commcare-cloud repo location
   export COMMCARE_CLOUD_REPO=/path/to/your/commcare-cloud

   # for local environments (other than $COMMCARE_CLOUD_REPO/environments)
   export COMMCARE_CLOUD_ENVIRONMENTS=/path/to/your/environments

You will need to either use ``uv run`` to run ``commcare-cloud`` commands inside
the ``COMMCARE_CLOUD_REPO`` directory, or activate the virtualenv using a
command like ``source $COMMCARE_CLOUD_REPO/.venv/bin/activate``.

Initialize log file
^^^^^^^^^^^^^^^^^^^

Required for Ansible log output. Ansible is a tool used internally by commcare-cloud.

.. code-block:: bash

    sudo touch /var/log/ansible.log
    sudo chmod 666 /var/log/ansible.log

Permissions will be tightened later by `commcare-cloud <env> bootstrap-users` or
`deploy_stack`, whichever is run first, if there is a machine in the `control`
group.

git-hook setup
^^^^^^^^^^^^^^

After completing the manual setup, make sure you install the git hooks.
From the ~/commcare-cloud directory, run the following:

.. code-block:: bash

   ./git-hooks/install.sh

This will make sure you never commit an unencrypted vault.yml file.


Point to your environments directory
------------------------------------

commcare-cloud needs to know where environments config directory is located to be able to run commands against the servers in that environment. See :ref:`reference/1-commcare-cloud/2-configuration:Configuring your CommCare Cloud Environments Directory` to understand what this directory is. The instructions on how this directory is created are part of the CommCare HQ installation docs in :ref:`quick-install` and :ref:`cchq-manual-install`.

Once you have installed commcare-cloud, you can do below to point commcare-cloud to your environments directory.

* Download the environments directory to any path that you own. Make sure the ownership permissions are set right.
* Run ``COMMCARE_CLOUD_ENVIRONMENTS=/path/to/environments/folder manage-commcare-cloud configure``.
