Pre-Deployment Checklist
========================

For each of the following questions, track the answers in a shared
document. Add a date and time to each answer to built a timeline of
progress.


Current Environment
-------------------

* What CommCare applications will be hosted in the local environment?

* Are users currently collecting data in any of the applications listed
  in the above question?

* If yes, how long has the application been live?

* What CommCare subscription do you currently have?

* Please provide a link to the architecture diagram for the planned
  system including development environments and / or integrations with
  3rd party tools.

* Name and job function of person migrating data from current
  environment to local environment

* Will data need to be migrated from the SaaS platform to your local
  instance?

* Please provide a link to the handover plan sequence for transitioning
  mobile devices from pointing to the cloud to the local server,
  including timelines and pre-requisites for each step.


Hardware
--------

* Provide a link to the server(s) specifications which will be used to
  host CommCare

* Will CommCare be hosted directly on these servers, or hosted in
  virtual machines on the hardware?

* How many CPUs does the server / cluster have?

* How much RAM does the server / cluster have?

* What is the size of the disk?

* What type of disk will you be using (SSD or HDD)?

* Are you planning on expanding Disk space as needed based on growth? If
  so, what will the process be for growing the disk volumes?


Software
--------

* Name and job function of person who will be installing CommCare on the
  server

* Name and job function of person managing CommCare post-deployment

* What version of Ubuntu is installed on the server / cluster?

* What domain name directs to the server?

* What is the Public IP address for the server?

* What email gateway will be used for the application?

* What SMS gateway will be used for the application?

* What kernel livepatching service will you be using (e.g. Ubuntu
  Advantage)?  For Ubuntu Advantage, what is the console output of
  running: ``canonical-livepatch status --verbose``

* If you are using a hypervisor, what hypervisor software are you using?
  What is the response time of the support subscription you have (e.g.
  one business day)?

* What are the update / maintenance schedules for the software and
  firmware of the components of the hosting environment? Are all
  elements currently up to date with the latest available versions?


Connectivity
------------

* Name of Internet Service Provider (ISP)

* Connectivity:
  + Mbps max burst download speed?
  + Mbps max burst upload speed?
  + Latency (ideally to some specific place)?
  + Bandwidth limits?

* What is the support plan when network issues arise? What is the name
  of the person accountable for running that plan, and what is the
  expected turnaround?

* Is the local subnet where CommCare will be installed able to reach
  network locations outside of the local network?


Recovery
--------

* How many minutes is provided for your server from your Uninterruptible
  Power Supply when an outage occurs?

* How is UPS failover to safe shutdown configured? How long does a safe
  shutdown take to complete once power is lost?

* What system will be responsible for creating backups for system
  recovery? What types of backups will exist?

* How frequently will backups be created? How long are individual
  backups retained?

* How will the backup recovery process be tested? Will it be tested on a
  periodic basis after initial evaluation?


Maintenance and Support Plan
----------------------------

* Name and job function of person who will be monitoring the forum and
  `CommCare changelog`_.

* Expected turnaround for both average and urgent changelog
  notifications.

* Name and job function of person doing CommCare Cloud deployments.

* What is the schedule on which CommCare will be updated and deployed

* What tool will you be using for ongoing monitoring of CommCare’s
  hosts? (e.g. DataDog, Nagios, etc)

* What tool will you be using for ongoing monitoring of CommCare’s
  application and service indicators? (e.g. DataDog, Prometheus, etc)

* Please provide a link to your disaster recovery plan

* Please provide a link to your issue triage process for receiving
  issues from end users


Security and Compliance
-----------------------

* What are the compliance certifications or procedures being followed at
  the physical data center?

* Will system compliance certifications (ISO 27001, SOC-2, CMMC) be
  audited for the system? If so, which and on what schedule?

* What physical security measures are in place at the data center?

* List all security appliances (web application firewall, intrusion
  detection monitoring, etc) which will be deployed along with CommCare
  services by type and version.

* How will access for system maintenance be performed and controlled?


CommCare Cloud
--------------

* Follow `the instructions to install CommCare Cloud`_. What is the
  console output when running the following on the control machine?
  ``commcare-cloud -h``


.. CommCare changelog: https://dimagi.github.io/commcare-cloud/changelog/
.. _the instructions to install CommCare Cloud: https://commcare-cloud.readthedocs.io/en/latest/reference/1-commcare-cloud/1-installation.html
