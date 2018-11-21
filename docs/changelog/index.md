# About this changelog

The following changes to `commcare-cloud` that require your attention,
newest first.

Changes that will require an action from anyone choosing
to update on or after the date listed will be maked "_action required_".
Those which are worth taking a look at but which may or may not require
an action on your part will be marked "_action optional_".


## Changelog

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
