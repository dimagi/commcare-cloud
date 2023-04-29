
Upgrading CitusDB
=================


#. Ensure that you have a full backup of all PostgreSQL data before starting the upgrade process.
#. Review the documentation:

   * `pg_upgrade <https://www.postgresql.org/docs/current/pgupgrade.html>`_
   * `citus <http://docs.citusdata.com/en/v9.4/admin_guide/upgrading_citus.html>`_

#. Test the upgrade process locally with Vagrant or on a test environment.

This upgrade is split into two parts:


#. Upgrade the 'citus' extension
#. Upgrade PostgreSQL

The citus extension should be upgraded prior to upgrading PostgreSQL.

In the below instructions:

.. code-block::

   OLD-VERSION: Current version of PostgreSQL that is running
   NEW-VERSION: Version being upgraded to
   OLD-PORT: Port that PostgreSQL is currently running on (defaults to 5432)


Upgrade 'citus'
---------------

Prepare for the 'citus' extension upgrade
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Run the ``deploy_citusdb.yml`` playbook to ensure your system is up to date
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   commcare-cloud <env> ap deploy_citusdb.yml


Upgrade the 'citus' extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Update ``public.yml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

public.yml:

.. code-block:: yaml

   citus_version: <new citus version>

2. Run the ``deploy_citusdb.yml`` playbook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   commcare-cloud <env> ansible-playbook deploy_citusdb.yml --tags citusdb -e postgresql_version=OLD-VERSION


3. Check the extension version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   commcare-cloud <env> run-shell-command citusdb -b --become-user postgres "psql -d DATABASE -c '\dx' | grep citus"


Upgrade PostgreSQL
------------------

Prepare for the PostgreSQL upgrade
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Update ``public.yml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

public.yml:

.. code-block:: yaml

   citus_postgresql_version: NEW-VERSION
   citus_postgresql_port: NEW-PORT  # this must be different from the current port

2. Run the ``deploy_citusdb.yml`` playbook to install the new version of PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   commcare-cloud <env> ansible-playbook deploy_citusdb.yml --tags citusdb


Perform the upgrade
^^^^^^^^^^^^^^^^^^^

1. Stop all processes connecting to the databases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

   commcare-cloud <env> run-module citusdb_master -b service "name=pgbouncer state=stopped"


2. Run the upgrade playbooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following commands can be used to perform the upgrade:

.. code-block::

   commcare-cloud <env> ansible-playbook pg_upgrade_start.yml --limit citusdb \
       -e old_version=OLD-VERSION -e new_version=NEW-VERSION [-e old_port=OLD-PORT]

   commcare-cloud <env> ansible-playbook pg_upgrade_standbys.yml --limit citusdb \
       -e old_version=OLD-VERSION -e new_version=NEW-VERSION [-e old_port=OLD-PORT]

   commcare-cloud <env> ansible-playbook pg_upgrade_finalize.yml --limit citusdb \
       -e old_version=OLD-VERSION -e new_version=NEW-VERSION


Follow the instructions given in the play output.

3. Revert to using the old port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you are satisfied with the upgrade you can revert the port change in ``public.yml``
and apply the changes.

.. code-block::

   commcare-cloud <env> ansible-playbook deploy_citusdb.yml
