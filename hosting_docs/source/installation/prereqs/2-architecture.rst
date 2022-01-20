Architecture Overview
=====================

.. image:: img/architecture_01.png

Primary Databases
-----------------

+------------------------------+-----------------------------+
| CouchDB (aka "couch")        | PostgreSQL (aka "postgres") |
+==============================+=============================+
| JSON documents               | Table rows                  |
+------------------------------+-----------------------------+
| Schemaless                   | Schema                      |
+------------------------------+-----------------------------+
| Map/reduce: Go through every | Dynamic queries             |
| doc in the table to create   |                             |
| an index. Run the query on   |                             |
| the indexed data.            |                             |
+------------------------------+-----------------------------+
| Not relational: Can't join   | Relational queries          |
| across tables.               |                             |
+------------------------------+-----------------------------+

We started with Couch. We struggled with some aspects of the way it
works, and so we added Postgres. All forms and cases are stored in
Postgres now.

A Couch document is analogous to a SQL row. This is the thing that the
"doc search" URL returns.


What's stored where?
--------------------

================   ===================   ========
PostgreSQL         CouchDB               Both
================   ===================   ========
Form Submissions   Users                 Products
Cases              Applications
Locations          Groups
UCR data           UCR configs
SMS models         Exports configs
Ledgers            Random config
Random config

UCRs are User-Configurable Reports; reports configured using
JSON-formatted definitions.

Raw data (forms and cases) → apply "data source config" → Data source →
apply "report config" → report output. e.g. A project may have a dozen
reports all based on the same data source. A UCR is a data source config +
a report config.

Data sources are stored in SQL, but report outputs are run in real time.

Things in the "Both" column are low priority to migrate, and for now are
going to live on both.

There has been a long period of Couch-to-SQL migration.

"Random config": We like SQL for this more, but a lot of this has been
on Couch historically, and we're going to leave it there for the time
being. There is no logical grouping of configs on SQL vs. Couch. About
300-400 documents in Couch (each one of which would need to be migrated
individually). About 200 documents in SQL. "Random config" is per
document. e.g.

* "create a new domain" is a request that creates a "domain" document
  type (in Couch).
* "invite new web user" is a request that creates a "web user" document
  type.


BlobDB
------

A "blob" is a "binary large object". BlobDB is the wrapper we've written
around storage services like S3 and Minio. It is used for

* Images
* Form Submissions (in XML)
* Form Definitions (in XML)
* Daily saved exports
* Cached restores
* Various generated files and assets

BlobDB stores "big" things as single units, where the data inside them
does not need to be queried. (The data that we do want to query is
copied out and stored elsewhere, e.g. form data.) Items are stored in
triplicate for redundancy.


Pillows
-------

Pillows are a custom ETL (extract, transform, load) system.

CouchDB & CommCare HQ --> Kafka --> Pillows --> Elastic & Postgres

Kafka is a distributed streaming platform; it passes streams of events,
or messages, from systems that produce events (e.g. CommCare says "I
just received this form submission") to systems that consume them (e.g.
Elasticsearch makes data from that form submission searchable.)

Pillows read the messages and do things that need to happen based on
those messages. e.g. "Based on this form submission I just read from
Kafka, I should be update those 3 UCRs." There would be a separate
pillow that would say, "Based on this form submission, I should update
Elasticsearch."

Pillows are custom code we wrote to consume messages from Kafka. We
could be relying more on external tools for things like this, and make
our set of pillows leaner. e.g. Elastic has a tool called LogStash that
is similar to pillows.

Random history: These are called "pillows" because they sit on top of
Couch. The system as a whole is called "pillowtop".


Elasticsearch
-------------

Elasticsearch is a secondary data store, optimized for search. Like
CouchDB, it is document-based and non-relational. Unlike CouchDB,
documents are mapped to a schema, and it supports dynamic querying.
CouchDB is supposed to be a robust storage system. Elasticsearch is
supposed to be a flexible search system.

Models stored:

* forms
* cases
* users
* domains
* groups
* ledgers
* SMS logs
* applications

Where they’re used:

* All standard reports
* The "groups or users" filter
* User list pages
* Backend for APIs, including for Excel dashboards
* Data Export Tool
* Backend for data exports
* Case Search


Elasticsearch is a secondary data store in that we could delete
everything in there and regenerate it if needed (but reports wouldn’t
work in the interim).

We store data in Elasticsearch in indices. Each index defines a schema.
A schema is called a "mapping" in Elasticsearch terminology. e.g. A
"form" is a schema. A "domain" is a schema.

Locations are loaded from PostgreSQL. Web user and mobile user lists are
loaded from Elasticsearch, but individual user pages are loaded from
PostgreSQL. If Elasticsearch is down, you will not be able to load the
list pages, but if you used a user UUID, you would be able to get to the
page for that user.

The same is true for forms and cases. i.e. Any standard reports wouldn’t
work, including Submit History and Case List reports, but you would be
able to get the page for a specific case or form.

For Case Search, Elasticsearch allows you to query the "case_properties"
section of the "case" schema as though it were specific to your project.


Celery
------

To open the Celery management UI, named "Celery Flower":

1. Check the inventory.ini file in your environments configuration.
2. Find which machine or machines host Celery.
3. Connect to port 5555 on one of those machines with a web browser.

The dashboard shows a list of task queues. (The "Worker Name" column
shows the queue names.)

Queues can accumulate a growing backlog if new tasks are added to the
queue faster than the queue's resources can process each one, which can
result in unexpected or unacceptable wait times before processing begins
on a task. (Confusingly developers refer to this state as "backed up",
which has nothing to do with a saved duplicate copy.)

A task can either the result of an action by a user ("Do this thing for
me"), or a scheduled task ("Do this thing once a month").

Celery will sometimes update a separate doc with the status of all its
tasks. Your browser will, separately, query that document every two
seconds and update a status page. This setup is most relevant for things
on HQ that show progress bars.

The output of some scheduled tasks is stored in Riak.

Some tasks are retried if they fail.

Examples of tasks:

* Exports: These have a task status that gets updated.
* Bulk user uploads: The status of an upload is saved. CommCare HQ users
  can see how many uploaded users were saved successfully.
* Bulk location uploads
* Case imports

Resources can be distributed by queues. A settings file spells these out.

Queues have priorities. These are configurable, and managed using
CommCare Cloud.


Redis
-----

Redis is a key-value store that offers fast, temporary storage. It
features a timeout, where data is removed after a given amount of time.
It  can be cleared, with short-term consequences.

It is used for caching. It stores frequently-used, expensive database
hits. And also session authentication, among other things.


From form submission to UCR
---------------------------

1. Mobile device submits form
2. Nginx proxy routes form to a web worker
3. (Django) CommCareHQ Django code processes
4. (Django) Looks up affected cases in PostgreSQL
5. (Django) Saves form and case changes to DB
6. (Django) Sends changes notifications to Kafka
7. (Django) Returns success response to phone
8. (Pillowtop) Pillowtop process sees relevant change in Kafka
9. (Pillowtop) Fetches UCR definition from CouchDB
10. (Pillowtop) Processes form according to definition
11. (Pillowtop) Saves row to UCR table in PostgreSQL


Exporting cases
---------------

+----------------------------------+-----------------------------------+
| Primary workflow                 | Background workflow               |
+==================================+===================================+
| 1. Browser requests a case       |                                   |
|    export.                       |                                   |
| 2. Nginx routes this to a        |                                   |
|    webworker.                    |                                   |
| 3. Webworker creates a task      |                                   |
|    status object in Redis.       |                                   |
+----------------------------------+-----------------------------------+
| 4. Triggers Celery task to       | 1. RabbitMQ receives task.        |
|    create export file.           | 2. Next available celery worker   |
| 5. Returns task ID to browser.   |    accepts task.                  |
| 6. Browser polls for updates and | 3. Fetches export configuration   |
|    displays progress bar.        |    from CouchDB.                  |
| 7. Django checks task status     | 4. Begins pulling cases from      |
|    object, returns current       |    PostgreSQL.                    |
|    progress.                     | 5. Processes cases according to   |
| 8. Browser polls for updates.    |    config.                        |
|                                  | 6. Regularly updates task status  |
|                                  |    object in Redis.               |
|                                  | 7. Writes Excel file to BlobDB.   |
|                                  | 8. Marks task status as "done" in |
|                                  |    Redis.                         |
+----------------------------------+-----------------------------------+
| 9. Django sees that the task is  |                                   |
|    marked as done, returns a     |                                   |
|    download link.                |                                   |
| 10. Browser requests download    |                                   |
|     file.                        |                                   |
| 11. Django fetches file from     |                                   |
|     BlobDB, returns it to        |                                   |
|     browser.                     |                                   |
+----------------------------------+-----------------------------------+
