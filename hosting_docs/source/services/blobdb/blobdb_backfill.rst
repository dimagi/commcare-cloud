
Back-fill all existing data
---------------------------

After things are set up to read from the new backend and fall back to the old backend,
you'll need to run some commands to migrate all existing data
from the old backend to the new backend.

First, make sure that the directory you'll use for logs exists:

.. code-block::

   cchq <env> run-shell-command django_manage 'mkdir /opt/data/blobdb-migration-logs; chown cchq:cchq /opt/data/blobdb-migration-logs' -b

Then run the migration in a tmux (or screen) with these good defaults options
(you can tweak the options if you know what you're doing):

.. code-block::

   cchq <env> django-manage --tmux run_blob_migration migrate_backend --log-dir=/opt/data/blobdb-migration-logs --chunk-size=1000 --num-workers=15

At the end, you may get a message saying that some blobs are missing
and a link to a log file that contains the info about which ones.
(If you don't get this message, congratulations! You can skip this step.)
Run the following command to check all the blobs in the file to get more info
about their status (the last arg is the log file that was printed out above):

.. code-block::

   cchq <env> django-manage --tmux check_blob_logs /opt/data/blobdb-migration-logs/migrate_backend-blob-migration-<timestamp>.txt

.. code-block::


   The output will look something like this:

tempfile: checked 2342 records
  Found in new db: 0
  Found in old db: 0
  Not referenced: 0
  Not found: 2342
XFormInstance: checked 42 records
  Found in new db: 0
  Found in old db: 0
  Not referenced: 21
  Not found: 21
...
```

Legend:


* ``Not referenced`` is OK. It means that the blob that was said to be "missing"
  isn't in the blobdb but also isn't referenced by its parent object anymore (this is only meaningful if ``BlobMeta.parent_id`` is a couch identifier that can be used to lookup the parent object), so it was likely deleted
  while the migration was running.
* ``Not found`` means that the missing blob is still referenced in blob metadata,
  but not found in either the old backend or new backend.
* ``Found in (new|old) db`` means that actually it is present in one of the backends,
  unlike originally reported. Re-run the ``check_blob_logs`` command with ``--migrate`` to migrate items "Found in old db".
