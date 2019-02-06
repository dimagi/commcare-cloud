# About this changelog

The following changes to `commcare-cloud` that require your attention,
newest first.

Changes that will require an action from anyone choosing
to update on or after the date listed will be maked "_action required_".
Those which are worth taking a look at but which may or may not require
an action on your part will be marked "_action optional_".


## Changelog

### **2019-02-01** [Generalize load case from fixture feature](0012-generalize-load-case-from-fixture.md) (_action required_)
Previously loading a case from a fixture required the fixture to be an attribute.
This change allows using non-attributes from the fixture.

### **2019-01-16** [Fix encrypted temp directory permissions](0011-fix-encrypted-tmp-permissions.md)
This is a followup to [Added encrypted temporary directory](./0001-add-encrypted-tmp.md)
in which we introduced an encrypted directory for temp files.
In its original implementation, this file was owned by root,
and processes were unable to write to it.

This changes the directory to be owned by cchq, allowing our processes to write to the file.

### **2019-01-02** [Restart nginx after every letsencrypt cert auto-renewal](0010-letsencrypt-restart-nginx.md)
Previously you had to manually restart nginx every time letsencrypt auto-renewed,
which was about every two months.

### **2018-12-15** [Blob Metadata Migration - part 2](0009-blob-metadata-part-2.md) (_action required_)
Form submission attachment metadata is being consolidated in the blob
metadata table in SQL. This migration consists of a series of commands that
will consolidate the data in your environment.

### **2018-09-24** [Blob Metadata Migration - part 1](0008-blob-metadata-part-1.md) (_action required_)
Blob metadata needs to be migrated from CouchDB to SQL. This migration
consists of a series of commands that will move the data in your environment.

### **2018-11-26** [Reorganize pillows](0007-reorganize-pillows.md) (_action required_)
Pillows read changes from kafka and do various processing such as sending them to
elasticsearch, transforming into a UCR table row etc. A doc for same change is read
multiple times for each processor, since there are separte pillows for each processor.
This is inefficient, so we have combined multiple processors that apply for a
given document type (also called `KAFKA_TOPIC`) such as form/case/user under
one pillow. For e.g. A new single `case-pillow` pillow replaces
various old pillows that process case changes such as `CaseToElasticsearchPillow`,
`CaseSearchToElasticsearchPillow`, `ReportCaseToElasticsearchPillow`,
and `kafka-ucr-main` etc. 

### **2018-11-20** [New Case Importer Celery Queue](0006-new-case-importer-celery-queue.md) (_action required_)
Importing cases is often a time-sensitive task, and prolonged backlogs are
very visible to users.  It will be useful to have a separate queue
specifically for case imports, to improve visibility into backups as well as
typical runtimes.  Additionally, this is a first step towards allocating
resources specifically for case imports, should that become necessary.

### **2018-08-16** [Support multiple Kafka brokers](0005-support-multiple-kafak-brokers.md) (_action required_)
Large scale deployments of CommCare require scaling out Kafka brokers to support the high
traffic volume (as well as for high availability). Up until now CommCare has only
supported a single broker.

### **2018-08-16** [Add queue for analytics tasks](0004-add-analytics-queue.md)
Tasks for analytics reporting have been separated into a new analytics celery queue.

### **2018-07-25** [Update Supervisor](0003-update-supervisor.md)
Ubuntu 14.04 `apt-get install supervisor` installs supervisor 3.0b.
We occasionally have issues that could be related to supervisor,
such as processes not stopping correctly.
To rule it out as a possible cause,
we decided it was better to be on a later version of supervisor,
and one that's not in beta.

### **2018-07-13** [Update supervisor service definitions](0002-supervisor-service-definitions.md) (_action required_)
There are several CommCare specific processes that are defined in supervisor
configuration files. This change decouples the process definitions from code.

### **2018-06-11** [Added encrypted temporary directory](0001-add-encrypted-tmp.md) (_action required_)
Some of the CommCare processes make use of temporary files to store client data
(such as data exports) so in order to keep that data protected we have modified
the setup to use an encrypted temporary directory.
