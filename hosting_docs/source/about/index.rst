About CommCareHQ
================

CommCare is a multi-tier mobile, server, and messaging based platform. The server part of the platform is called as CommCareHQ. The platform enables end-users to build and configure content through a user interface, deploy that application to Android or J2ME based devices, and receive data back in real-time (if connected) from the mobile applications.  In addition, content may be defined that leverages bi-directional messaging to end-users via API interfaces to SMS Gateways, E-mails systems, or other messaging services.  The system leverages multiple persistence mechanisms, analytical frameworks, and open source libraries.

CommCareHQ is offered through Dimagi managed cloud with free and tiered subscription models at https://wwww.commcarehq.org. Please refer to https://www.commcarehq.org/pricing/ and https://dimagi.com/services/ for information on this. If you are interested in self hosting CommCareHQ this guide is for you.


About this Guide
----------------

This documentation contains guides and reference material on how to self host CommCareHQ locally. It covers various deployment types, infrastrucutre and team requirements to host CommCareHQ, installation instructions for single and multi server deployment and how to manage CommCareHQ deployment through the entire hosting lifecycle.

This documentation is relevant for those who want to host CommCareHQ locally on their infrastructure. If you are looking for something else please see below. 

- If you are interested in using CommCareHQ without having to host yourself, please check out our clould offering at https://www.commcarehq.org.
- Docs on how to use CommCareHQ https://wiki.commcarehq.org/display/commcarepublic/Home
- Setting up CommCareHQ locally for development https://github.com/dimagi/commcare-hq/blob/master/DEV_SETUP.md
 

A word of caution on Self Hosting
---------------------------------

CommCare HQ is a complex, distributed software application, made up of dozens of processes and several pieces of third-party open source database software. It has been built for scale rather than simplicity, and as a result even for small deployments a CommCare server or server cluster can be challenging to maintain. An organization endeavoring to manage their own CommCare server environment must be willing to devote considerable effort and system administration capacity not only in the initial phases of provisioning, setup, and installation, but in steady state as well.

If you or your organization is hosting or interested in hosting its own CommCare server environment, we strongly suggest you to read about the :ref:`hosting-considerations` and prerequisites required to host CommCare locally at :ref:`hosting-prereqs`. One you understand the prerequisites you may refer to :ref:`quick-install` or :ref:`multi-server-install` depending on your hosting type.

How to use this Guide
---------------------

This