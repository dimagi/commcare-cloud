Securing CommCareHQ
===================

Security is once of the most important things when dealing with web applications. This guide gives high level overview of security considerations to protect the data that is collected using your CommCareHQ instance. Note that this just gives hints in the direction of the security and is in no way exhaustive.

Introduction
------------

A web application exposed to public internet has many levels where an attack is possible such as application, host operating system, network and even physical levels. In a Cloud environment, the cloud service provider handles the security upto operating system. But when hosting on premises all of this responsiblity falls upon the team hosting the application. 

It is very important to design an end-to-end hosting architecture and processes to maximize security at all levels. In addition, there might be government regulations and legal requirements to be met when hosting locally that you may have to know.

Below are few architecture references from the industry to help you understand number of considerations when designing a secure hosting environment.

#. https://www.cisco.com/c/dam/en/us/solutions/collateral/enterprise/design-zone-security/safe-secure-dc-architecture-guide.pdf
#. https://www.oracle.com/a/ocom/docs/oracle-cloud-infrastructure-security-architecture.pdf
#. https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-123.pdf

Below we provide few of such considerations that we recommend at a minimum.

.. note::

  CommCareHQ is an open source platform developed by Dimagi. While Dimagi does its best to make CommCareHQ secure by following all the industry best practices including annual security audits, if you self host CommCareHQ, you are solely responsible for the safety of your users and the data collected through your CommCareHQ instance.


Application Security
--------------------

Application refers to all the services that are accessible for users mostly through HTTP. In the context of CommCareHQ, it's the CommCareHQ website that is hosted by you and any other services that have HTTP endpoints such as Elasticsearch and Celery Flower. Here are few things that you must take care of to ensure safety of the application services.

#. **Access Management**

	- CommCareHQ has finegrained `roles and permissions <https://confluence.dimagi.com/display/commcarepublic/Roles+and+Permissions>`_ based access management. When registering users make sure they have appropriate roles and permissions.

	- For users with administrative privileges make sure they setup and use `Two Factor Authentication <https://confluence.dimagi.com/display/commcarepublic/Setting+up+Two-Factor+Authentication>`_.

#. Refer to ``Privacy and Security`` section in `Project Space Settings <https://confluence.dimagi.com/display/commcarepublic/Project+Space+Settings>`_ and configure as necessary.

#. Be upto date with CommCareHQ and commcare-cloud by following :ref:`operations/4-maintenance:Expectations for Ongoing Maintenance`.

#. Make sure to configure SSL certificate using docs at :ref:`services/nginx/ssl:SSL certificate setup for nginx`.


Host and Disk Security
----------------------

#. **Access management** Make sure that access to virtual machines is done using SSH keys and not passwords. Refer to :ref:`reference/3-user-access-security:User Access Management` to know how this is done using commcare-cloud. Implement any other best practices such as enabling access through VPN and logging SSH access etc as necessary.

#. **Data Encrypttion** When you deploy with CommCareHQ with commcare-cloud all the drives that store user data are automatically encrypted. If you are storing data anywhere else, make sure that the drives are encrypted.

#. **Secrets** All the passwords are stored in the ansible encrypted vault file. Never expose these passwords and store and share the password for the vautl file securely.

#. Make sure you have a process in place to get alerts on security patches for the operating system and other important libraries.


Network and Physical Security
----------------------------

#. Use VPN to access virtual machines when outside the LAN.

#. Make sure to implement necessary firewall rules to enable restricted access to the virtual machines.

#. If you are in a hosting setup where other applications are hosted alongside with CommCareHQ, you may have to configure additional network functionalities.

#. Implement necessary protocols to secure access to the physical servers at the data center or server room.
