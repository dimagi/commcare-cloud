Roles And Responsibilities for Hosting CommCare
===============================================

------------
Introduction
------------

This section is intended to convey the different roles and
responsibilities which are associated with setting up and maintaining a
privately hosted local cloud instance of CommCare HQ, along with
expectations around what skills and knowledge are needed to fulfill
them. An individual person or firm may fulfill a number of these roles,
but they are separated here to clarify the skills and availability
required to fulfill them.

These are based directly on Dimagi’s process and experience providing
CommCare HQ as a managed SaaS platform and managed cloud, but they may
not be comprehensive depending on specific local or organizational
needs.

-----------------------
Infrastructure Provider
-----------------------

Responsible for providing the physical resources needed by the cluster
(servers, network interfaces, etc.) When providing infrastructure as a
service to other businesses we’d refer to this as the “Cloud Services
Provider.”

Scope of Work
^^^^^^^^^^^^^

* Virtual Machine hosting
* Support and debugging for non-responsive hardware

Skills and Knowledge Required
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* VMWare or other virtualization technology
* Network interfaces, including firewalls and load balancing

Sample Providers
^^^^^^^^^^^^^^^^

* AWS EC2
* Rackspace Managed Infrastructure
* Microsoft Azure
* IBM Softlayer

------------------
Cluster Management
------------------

Responsible for understanding and maintaining the physical
infrastructure that has been provided and ensuring its availability and
reliability.

Scope of Work
^^^^^^^^^^^^^

* Installing operating systems and configuring cloud resources to spec
* Applying security patches and operating system updates
* Establishing protocols for backups and system recovery
* Monitoring the servers for intrusion detection and other active
  security monitoring
* Responding to active threats to availability and security like DDOS
  attacks

Skills and Knowledge Required
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* General Linux system administration
* Understanding of virtual machine resources, network infrastructures,
  and other core IT concepts
* Familiarity with backup and recovery schemes for the relevant
  components of the CommCare infrastructure
* General knowledge of security best practices

Sample Providers
^^^^^^^^^^^^^^^^

* Rackspace Managed Services
* AWS Managed Services

.. note ::
    Commercially, this offering is generally made on top of managed
    infrastructure by the same company, and the two are traditionally
    bundled.

--------------------------------------------------
Cloud Application Management / Operations Engineer
--------------------------------------------------

Responsible for deploying the CommCare web application and dependent
services, and keeping them up-to-date.

When this role and the role above are provided together as a service,
that shared role is referred to as a “Managed Services Provider”.

Scope of Work
^^^^^^^^^^^^^

* Sizing and scoping the cloud infrastructure needs
* Provisioning servers with the cloud software applications
* Debugging and maintaining individual services that are part of the
  cloud
* Keeping the cloud software up to date with new changes
* Supporting data migrations and other ‘on server’ (as opposed to ‘in
  application’) operations tasks
* Monitoring the status and availability of individual services and
  addressing issues

Skills and Technologies
^^^^^^^^^^^^^^^^^^^^^^^

* Familiarity with Python and ability to interpret Python tracebacks
* Familiarity with Linux system administration and management
* Experience with deploying and maintaining a cluster of servers hosting
  a web application which is dependent on federated services

Expected to learn in the first 1-3 months of working on CommCare Cloud.
*Please note that the deployment of the local system won't be successful
unless the team as a whole has experience or some level of comfort with
these tools*:

* Familiarity or capacity to learn the core components of a CommCare
  cloud
  + Web Proxy Server (nginx)
  + SQL database (PostgreSQL)
  + Messaging queue (RabbitMQ)
  + Cache server (Redis)
  + Search index (Elasticsearch)
  + Object Storage (RiakCS)
  + Distributed Message Log (Kafka)
  + Distributed Configuration management (Zookeeper)
* Familiarity with the frameworks relied upon by our operations tools
  + Ansible
  + Fabric
  + Monit
  + Supervisor
  + EncryptFS
  + LVM

Sample Providers
^^^^^^^^^^^^^^^^

“Managed Application Hosting”:

* Rackspace SAP Hosting
* IBM Managed Application Services

----------------------------------
CommCare Application Administrator
----------------------------------

Responsible for configuring CommCare HQ from inside of the web
application.

Scope of Work
^^^^^^^^^^^^^

* User and application configuration
* Processing tech support direction when internal maintenance tools need to be run within the HQ web app
* Providing technical support for end users of the application

Skills and Technologies
^^^^^^^^^^^^^^^^^^^^^^^

* Familiarity with CommCare HQ
