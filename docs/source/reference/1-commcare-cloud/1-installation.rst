.. _cchq-installation:

Installation
============

commcare-cloud can be installed on a local machine or on a remote control machine that's part of the CommCare HQ environment. We recommend installing on a control machine.

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

Run this command to verify that you are in the home directory of the ``admin`` user.

.. code-block:: bash

   admin@control.example.com:~$ pwd
   /home/admin

Step 2.
^^^^^^^

Pull commcare-cloud source code.

.. code-block:: bash

   admin@control.example.com:~$ git clone https://github.com/dimagi/commcare-cloud.git

Verify that created a directory called ``commcare-cloud``\ :

.. code-block:: bash

   admin@control.example.com:~$ ls commcare-cloud/
   commcare-cloud-bootstrap  environments  MANIFEST.in   setup.py
   control                   fabfile.py    provisioning  src
   dev_requirements.txt      git-hooks     README.md     tests
   docs                      Makefile      scripts       Vagrantfile

If you see something like

.. code-block:: bash

   ls: cannot access commcare-cloud: No such file or directory

then the ``git clone`` command did not run correctly.
Make sure you have git installed and run it again
with ``--verbose`` to give more logging output.

If you see

.. code-block:: bash

   fatal: destination path 'commcare-cloud' already exists and is not an empty directory.

Run the following commands to update the existing commcare-cloud repository

.. code-block:: bash

   admin@control.example.com:~$ cd commcare-cloud
   admin@control.example.com:~$ git checkout master
   admin@control.example.com:~$ git pull
   admin@control.example.com:~$ cd ..

Step 3.
^^^^^^^

Run the install script.

.. code-block:: bash

   admin@control.example.com:~$ source commcare-cloud/control/init.sh

and when you see it ask you this:

.. code-block:: bash

   Do you want to have the CommCare Cloud environment setup on login?
   (y/n):

answer with ``y``.
This will make ``commcare-cloud`` available to run every time you log in.

To check that commcare-cloud is now installed, run

.. code-block:: bash

   admin@control.example.com:~$ commcare-cloud -h
   usage: commcare-cloud [-h] [--control]

                         {64-test,development,echis,icds,icds-new,pna,production,softlayer,staging,swiss}
                         {bootstrap-users,ansible-playbook,django-manage,aps,tmux,ap,validate-environment-settings,deploy-stack,service,update-supervisor-confs,update-users,ping,migrate_couchdb,lookup,run-module,update-config,mosh,after-reboot,ssh,downtime,fab,update-local-known-hosts,migrate-couchdb,run-shell-command}
                         ...

...and then much more help output describing each possible command.


If you get to this point, congratulations! ``commcare-cloud`` is installed.

Manual Installation
-------------------

You will need python 3.10 installed to follow these instructions. See
:ref:`installation/2-manual-install:Upgrade to Python 3.10` for instructions on
getting it installed on Ubuntu 18.04. Steps for other operating systems may
differ.


Setup
^^^^^

Download and run the ``control/init.sh`` script. This should be run from your home directory:

.. code-block::

   source <(curl -s https://raw.githubusercontent.com/dimagi/commcare-cloud/master/control/init.sh)

You will see the following prompt

.. code-block::

   Do you want to have the CommCare Cloud environment setup on login?
   (y/n):

If you answer 'y' then a line will be added to your .profile that will automatically run ``source ~/init-ansible``
when you log in, sets up the commcare-cloud environment.
Otherwise, you can choose to run ``source ~/init-ansible`` manually to setup the environment during future sessions.

You may now use ``commcare-cloud`` or its shorter alias ``cchq`` whenever you're in the virtualenv.

Manual setup
^^^^^^^^^^^^

If you'd rather use your own virtualenv name or a different commcare-cloud repo
location, or if the script above did not work.

Setup and activate the virtualenv
"""""""""""""""""""""""""""""""""

**NOTE**: *The virtualenv name and location may be customized, below example uses ``cchq``
and ``~/.virtualenvs/cchq``. Adjust according to your preferred configuration.*

.. code-block:: sh

   # using venv
   python3.10 -m venv ~/.virtualenvs/cchq
   source ~/.virtualenvs/cchq/bin/activate

   # -- or --

   # using pyenv
   pyenv virtualenv 3.10 cchq
   pyenv activate cchq


Install commcare-cloud with pip
"""""""""""""""""""""""""""""""

.. code-block:: sh

   # IMPORTANT: ensure the virtual environment is activated
   git clone https://github.com/dimagi/commcare-cloud.git
   cd ./commcare-cloud
   pip install --upgrade pip-tools
   pip-sync requirements.txt
   pip install -e .
   manage-commcare-cloud install

   # (Optional) To use commcare-cloud (cchq) without needing an active virtual
   # environment, run the following and respond to the prompts.
   manage-commcare-cloud configure

If you opted out of the final ``manage-commcare-cloud configure`` step and you
have a local environments directory or cloned the repo somewhere other than
``~/commcare-cloud`` you should set one or both of the following in your bash
profile (\ ``~/.profile``\ ) as needed:

.. code-block:: sh

   # for non-standard commcare-cloud repo location
   export COMMCARE_CLOUD_REPO=/path/to/your/commcare-cloud

   # for local environments (other than $COMMCARE_CLOUD_REPO/environments)
   export COMMCARE_CLOUD_ENVIRONMENTS=/path/to/your/environments

git-hook setup
^^^^^^^^^^^^^^

After completing the manual setup, make sure you install the git hooks.
From the ~/commcare-cloud directory, run the following:

.. code-block::

   (cchq)$ ./git-hooks/install.sh

This will make sure you never commit an unencrypted vault.yml file.


Point to your environments directory
------------------------------------

commcare-cloud needs to know where environments config directory is located to be able to run commands against the servers in that environment. See :ref:`reference/1-commcare-cloud/2-configuration:Configuring your CommCare Cloud Environments Directory` to understand what this directory is. The instructions on how this directory is created are part of the CommCare HQ installation docs in :ref:`quick-install` and :ref:`cchq-manual-install`.

Once you have installed commcare-cloud, you can do below to point commcare-cloud to your environments directory.

* Download the environments directory to any path that you own. Make sure the ownership permissions are set right.
* Run ``COMMCARE_CLOUD_ENVIRONMENTS=/path/to/environments/folder manage-commcare-cloud configure``.
