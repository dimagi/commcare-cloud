# About this changelog

The following changes to `commcare-cloud` that require your attention,
newest first.

Changes that will require an action from anyone choosing
to update on or after the date listed will be maked "_action required_".
Those which are worth taking a look at but which may or may not require
an action on your part will be marked "_action optional_".


## Changelog

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
Some of the CommCare processes make use of temporary files to store client data (such as data exports) so in order to keep that data protected we have modified the setup to use an encrypted temporary directory.
