
Tips and Tricks
===============

The following list outlines some useful things that may help when doing specific tasks. Before using them
you should make sure you understand what it is doing and when it is appropriate to use.

Update localsettings in a specific release
------------------------------------------

Limitations
~~~~~~~~~~~

This only works for CommCare processes and not for Formplayer.

Usage scenario
~~~~~~~~~~~~~~

Testing configuration changes without impacting running processes

Setup
~~~~~

Create a new release:

.. code-block:: shell

   commcare-cloud <env> deploy commcare --private [--limit ...]

Note down the release folder location: ``/home/cchq/www/<env>/releases/YYYY-MM-DD_HH.MM``

Update configuration in that release only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   commcare-cloud <env> update-config --limit [LIMIT] -e code_home=[RELEASE FOLDER]

This will override the default value of the ``code_home`` variable which normally points to the
``current`` release.

Choosing a value for ``LIMIT``\ :


* If you did not use ``--limit``\ , set ``LIMIT`` to ``django_manage``
* If you did use ``--limit``\ , set ``LIMIT`` to the same value as used before.
