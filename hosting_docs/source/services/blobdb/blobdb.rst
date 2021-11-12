
BlobDB
======

.. contents:: Table of Contents
    :depth: 2

Usage in CommCare
-----------------

The BlobDB refers to the internal service used by CommCare to store binary data or `blobs <https://en.wikipedia.org/wiki/Binary_large_object>`_.
The interal API is abstracted from the backend service allowing different backends to be used. Currently supported
backends are:


* File system

  * This backend is used for small CommCare deployments where all CommCare services can be run on a single VM / server.

* S3 compatible service (S3, OpenStack Swift, Minio, Riak CS etc.) 

  * For larger deployments an Object Storage service is required to allow access to the data from different VMs.

The BlobDB is made up of 2 components:


* PostgreSQL metadata store

  * This keeps track of the object key and it's association to the relevant CommCare models.

* Key based storage service

  * This the actual service where the data is stored. Data can be retrieved by using the object key.

Examples of data that is stored in the BlobDB:


* Form XML
* Form attachments e.g. images
* Application multimedia
* Data exports
* Temporary downloads / uploads

Migrating from one BlobDB backend to another
--------------------------------------------

It is possible to migrate from one backend to another. The process is described in the following documents:


* `Migrate from one S3 backend to another <blobdb/migrate-s3-to-s3.md>`_
* `Migrate from File System backend to S3 backend <blobdb/migrate-fs-to-s3.md>`_

.. toctree::
   :maxdepth: 4

   /services/blobdb/migrate-fs-to-s3.rst
   /services/blobdb/migrate-s3-to-s3.rst
   /services/blobdb/blobdb_backfill.rst