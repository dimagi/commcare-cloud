###############
Getting Started
###############


About CommCareHQ
----------------

CommCare is a multi-tier mobile, server, and messaging based platform. The server part of the platform is called as CommCareHQ. The platform enables end-users to build and configure content through a user interface, deploy that application to Android or J2ME based devices, and receive data back in real-time (if connected) from the mobile applications.  In addition, content may be defined that leverages bi-directional messaging to end-users via API interfaces to SMS Gateways, E-mails systems, or other messaging services.  The system leverages multiple persistence mechanisms, analytical frameworks, and open source libraries.

CommCareHQ is offered through Dimagi managed cloud with free and tiered subscription models at https://wwww.commcarehq.org. Please refer to https://www.commcarehq.org/pricing/ and https://dimagi.com/services/ for information on this. If you are interested in self hosting CommCareHQ this guide is for you.


About this Guide
----------------

This documentation contains tutorials, guides, and reference material on how to self host CommCareHQ, infrastructure and team requirements, installation instructions for single and multi server deployment, and how to manage CommCareHQ deployment through the entire hosting life-cycle. This documentation is relevant for those who want to host CommCareHQ locally on their infrastructure.

If you are looking for something else please see below. 

- If you are interested in using CommCareHQ without having to host yourself, please check out our cloud offering at https://www.commcarehq.org.
- Docs on how to use CommCareHQ https://wiki.commcarehq.org/display/commcarepublic/Home
- Setting up CommCareHQ locally for development https://github.com/dimagi/commcare-hq/blob/master/DEV_SETUP.md
 

A word of caution on Self Hosting
---------------------------------

CommCare HQ is a complex, distributed software application, made up of dozens of processes and several pieces of third-party open source database software. It has been built for scale rather than simplicity, and as a result even for small deployments a CommCare server or server cluster can be challenging to maintain. An organization endeavoring to manage their own CommCare server environment must be willing to devote considerable effort and system administration capacity not only in the initial phases of provisioning, setup, and installation, but in steady state as well.

If you or your organization is hosting or interested in hosting its own CommCareHQ server environment, we strongly suggest you to read about the :ref:`hosting-considerations` and prerequisites required to host CommCare locally at :ref:`hosting-prereqs`.

How to use this guide to self host CommCareHQ
---------------------------------------------


1. Read and understand all the prerequisites for hosting at :ref:`hosting-prereqs`.
2. Figure out which installation is most suitable for you using :ref:`deployment-options` doc.
3. Use one of the deployment guides :ref:`here <deploy-commcarehq>` to install and configure all the required services to run CommCareHQ.
4. For managing, updating CommCareHQ, monitoring and troubleshooting check out :ref:`operations-maintenance`.
5. To understand how each service is used and perform common operations related to services checkout the section on :ref:`service-guides`.
6. To scale services when required consult the section on :ref:`how-to-scale`.
7. Ensure you have setup backups correctly and have a disaster recovery plan using :ref:`backups-dr`.
