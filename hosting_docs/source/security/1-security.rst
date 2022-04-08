Securing CommCareHQ
===================

Security is one of the most important things when dealing with web applications. This guide gives high level overview of security considerations to protect the data that is collected using a CommCareHQ instance. Note that this just gives hints in the direction of the security and is in no way exhaustive.

Introduction
------------

A web application exposed to public internet has many levels where an attack is possible such as application, host operating system, network and even physical levels. In a cloud environment, the cloud service provider handles the security up to operating system. But when hosting on premises all of this responsibility falls upon the team hosting the application.

It is very important to design an end-to-end hosting architecture and processes to maximize security at all levels. In addition, there might be government regulations and legal requirements to be met when hosting locally that the local hosting team may need to be aware of.

Below are few security focused architecture from the industry as a reference to understand the number of considerations when designing a secure hosting environment.

#. https://www.cisco.com/c/dam/en/us/solutions/collateral/enterprise/design-zone-security/safe-secure-dc-architecture-guide.pdf
#. https://www.oracle.com/a/ocom/docs/oracle-cloud-infrastructure-security-architecture.pdf
#. https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-123.pdf

Below we provide few of such considerations that we recommend at a minimum.

.. note::

  CommCare and its server platform CommCareHQ are Open Source software, primarily developed by Dimagi. These are made available to the community under the terms of its Open Source licensing without warranty.

  We regularly undertake security efforts like penetration testing, audits of the software code, and reviews to ensure that the system functionality is sufficient to meet compliance commitments that we make to our commercial customers in providing our SaaS service. We believe that these demonstrate that CommCare can meet very high standards of scrutiny when deployed appropriately.

  To best support our community of practice, below we provide security best practices which are common to the security needs of our partners. These materials are provided for reference without warranty for their accuracy or sufficiency to meet a particular standard of security, and do not constitute any commitment from the authors or owners of the code.


Application Security
--------------------

Application refers to all the services that are accessible for users mostly through HTTP. In the context of CommCareHQ, it's the CommCareHQ website that is being hosted and any other services that have HTTP endpoints such as Elasticsearch and Celery Flower. Here are few things that must be taken care of to ensure safety of the application services.

#. **Access Management**

	- CommCareHQ has finegrained `roles and permissions <https://confluence.dimagi.com/display/commcarepublic/Roles+and+Permissions>`_ based access management. When registering users make sure they have appropriate roles and permissions.

	- For users with administrative privileges make sure they set up and use `Two Factor Authentication <https://confluence.dimagi.com/display/commcarepublic/Setting+up+Two-Factor+Authentication>`_.

#. Refer to ``Privacy and Security`` section in `Project Space Settings <https://confluence.dimagi.com/display/commcarepublic/Project+Space+Settings>`_ and configure as necessary.

#. Be up to date with changes and security updates for CommCareHQ and commcare-cloud by following :ref:`operations/4-maintenance:Expectations for Ongoing Maintenance`.

#. Make sure to configure SSL certificate using docs at :ref:`services/nginx/ssl:SSL certificate setup for nginx`.


Host and Disk Security
----------------------

#. **Access management** Make sure that access to virtual machines is done using SSH keys and not passwords. Refer to :ref:`reference/3-user-management:User Access Management` to know how this is done using commcare-cloud. Implement any other best practices such as enabling access through VPN and logging SSH access etc as necessary.

#. **Data Encrypttion** When CommCareHQ is deployed with commcare-cloud all the drives that store user data are automatically encrypted. If the data is stored anywhere else, it must be made sure that the data is stored only in encrypted drives.

#. **Secrets** All the passwords are stored in the ansible encrypted vault file. Never expose these passwords and store and share the password for the vault file securely.

#. It's recommended to take support contracts for Ubuntu and any other virtualization software.

#. Make sure that there is a process in place to get alerts on security patches for the operating system and other important libraries.


Network and Physical Security
----------------------------

#. Use VPN to access virtual machines when outside the LAN.

#. Make sure to implement necessary firewall rules to enable restricted access to the virtual machines.

#. If the hosting hardware is shared with other applications alongside  CommCareHQ, additional network functionalities may need to implemented to ensure security isolation of the applications.

#. Implement necessary protocols to secure access to the physical servers at the data center or server room.
