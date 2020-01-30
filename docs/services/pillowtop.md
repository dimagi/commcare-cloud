# Pillowtop

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

* [Change Feeds](https://commcare-hq.readthedocs.io/change_feeds.html)
* [Pillows](https://commcare-hq.readthedocs.io/pillows.html)

## Usage in CommCare

CommCare uses pillows to populate its secondary databases. These databases are used
for reporting and also back some of the CommCare features like APIs.

These databases are:
* Elasticsearch
* SQL custom reporting tables

## Guides
- [Splitting a pillow](pillowtop/split.md)
