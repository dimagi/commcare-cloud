
Pillowtop
=========

.. contents:: Table of Contents
    :depth: 2


Pillowtop is an internal framework built in CommCare which is used for asynchronous stream
processing of data.

A *pillow* is a class build in the *pillowtop* framework.
A pillow is a subscriber to a change feed. When a change is published the pillow
receives the document, performs some calculation or transform, and publishes it
to another database.

In general a *change feed* refers to a Kakfa topic or topics but could also be a CouchDB
change feed.

More information on the architecture and code structure are available in the CommCare
documentation:


* `Change Feeds <https://commcare-hq.readthedocs.io/change_feeds.html>`_
* `Pillows <https://commcare-hq.readthedocs.io/pillows.html>`_

Usage in CommCare
-----------------

CommCare uses pillows to populate its secondary databases. These databases are used
for reporting and also back some of the CommCare features like APIs.

These databases are:


* Elasticsearch
* SQL custom reporting tables


Splitting a pillow
------------------

In some cases a pillow may contain multiple processors. It is sometimes desirable to split
up the processors into individual OS processes. The most compelling reason to do this is if
one of the processors is much slower than the others. In this case having the slow processor
separated allows the other's to process at a faster pace. It may also be possible to deploy
additional processing capacity for the slow one.

The the following steps we will be splitting the ``FormSubmissionMetadataTrackerProcessor``
out from the ``xform-pillow``.

The ``xform-pillow`` has multiple processors as can be seen from the
`CommCare docs <https://commcare-hq.readthedocs.io/pillows.html#corehq.pillows.xform.get_xform_pillow>`_.
The ``FormSubmissionMetadataTrackerProcessor`` can be disabled by setting
``RUN_FORM_META_PILLOW`` to ``False`` in the Django settings file. We can also see that the
``FormSubmissionMetadataTrackerProcessor`` is used by the ``FormSubmissionMetadataTrackerPillow``.

So in order to split the ``FormSubmissionMetadataTrackerProcessor`` into its own pillow process
we need to do the following:


#. 
   Update the environment configuration


   * 
     Add the new pillow to ``<env>/app-processes.yml``

     .. code-block:: yaml

          pillows:
            'pillow_host_name':
              FormSubmissionMetadataTrackerPillow:
                num_processes: 3

   * 
     Update the ``RUN_FORM_META_PILLOW`` to disable the processor in the current pillow:

     .. code-block:: yaml

          localsettings:
            RUN_FORM_META_PILLOW: False

#. 
   Stop the current pillow

   .. code-block:: bash

       cchq <env> service pillowtop stop --only xform-pillow

#. 
   Create new checkpoints for the new pillow

   .. code-block:: bash

       cchq <env> django-manage --tmux split_pillow_checkpoints xform-pillow FormSubmissionMetadataTrackerPillow

   Note: ``--tmux`` is necessary to allocate a terminal for the command which allows you to respond to any
   confirmation prompts.

#. 
   Deploy the new pillow

   .. code-block:: bash

       cchq <env> update-supervisor-confs

#. 
   Ensure all the pillows are started

   .. code-block:: bash

       cchq <env> service pillowtop start

