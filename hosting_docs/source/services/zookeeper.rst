Zookeeper
=====

---------
Resources
---------

* `Upgrade guide <upgrading-kafka>`_
* `Command line tools <https://cwiki.apache.org/confluence/display/KAFKA/Replication+tools>`_

------------
Dependancies
------------

* Java

-----
Setup
-----

Zookeeper is installed on each host in the *Zookeeper* inventory group.

---------------
Upgrading Zookeeper
---------------


* Current default version: 3.2.0
* Example target version: 3.7.1

#. 
   Ensure that the Zookeeper config is up to date

   .. code-block::

       $ cchq <env> ap deploy_kafka.yml --tags=zookeeper

#. 
   Update the Zookeeper version number in ``public.yml``

    **environments/\ :raw-html-m2r:`<env>`\ /public.yml**

   .. code-block::

       zookeeper_version: 3.7.1
       zookeeper_download_sha1: <SHA1_Encryption_key>

#. 
   Upgrade the Zookeeper binaries and config 

   .. code-block::

       $ cchq <env> ap deploy_kafka.yml --tags=zookeeper --limit <server>

#. 
   Upgrade the servers one at a time Once you have done so, the servers will be running the latest version   and you can verify that the cluster's behavior and performance meets expectations. It is still possible to downgrade at this point if there are any problems.

#. 
   Check whether zookeeper service is up and running

   .. code-block::

       $ cchq <env> run-shell-command <zookeeper_host> "service zookeeper-server status"

#. 
   Run check_services and make sure all services are running fine.

   .. code-block::

       $ cchq <env> django-manage check_services