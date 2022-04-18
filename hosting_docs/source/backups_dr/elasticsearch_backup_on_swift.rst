
ElasticSearch Backup on Swift API
=================================

We normally do the backup of ElasticSearch using ElasticSearch backup plugin which allows us to take backup
on external seervices compatible with S3. In Few cases where S3 is not availble we can sort to 
other solutions.
This documentaion details the same process for backing up on Swift API of OpenStack
Plugin used : https://github.com/BigDataBoutique/elasticsearch-repository-swift

Configuring and Testing.
------------------------

To install the plugin on the ansible server. 


* install the plugin using elasticsearch plugin binary. 
  ```bash

/opt/elasticsearch-1.7.6/bin/plugin install org.wikimedia.elasticsearch.swift/swift-repository-plugin/1.7.0```

.. code-block::


   * To create a Repo for the sanpshot
   ```bash

   curl -XPUT 'http://<ip-address>:9200/_snapshot/<env>_es_snapshot' -d '{
   >         "type": "swift",
   >         "settings": {
   >             "swift_url": "https://<aurl-address>/auth/v1.0/",
   >             "swift_container": "nameofthecontainer",
   >             "swift_username": "XXXXXX",
   >             "swift_password": "XXXXX",
   >             "swift_authmethod": ""
   >         }
   >     }'
   {"acknowledged":true}


* To take a snapshot
  ```bash

curl -X PUT "localhost:9200/_snapshot/\ :raw-html-m2r:`<env>`\ _es_snapshot/snapshot_1?wait_for_completion=true"

.. code-block::


   * To Verify the snapshot.
   ```bash

   curl -X GET "<ip-address>:9200/_snapshot/<env>_es_snapshot/_all"


* To restore a snapshot of date say 2018/10/05. 
  ```bash

curl -X POST "\ :raw-html-m2r:`<ip-address>`\ :9200/_snapshot/\ :raw-html-m2r:`<env>`\ _es_snapshot/\ :raw-html-m2r:`<env>`\ _es_snapshot_2018_10_5/_restore"

.. code-block::



   ## Configuring in Ansible
   Once you can check that above process is working fine you can proceed with configuring the same in Ansible.

   Add the following entries in `public.yml` of the environemtn you want to configure.  
   ```bash
   # ElasticSearch Backup on Swift API
   backup_es_swift: True
   swift_container: "nameofthecontainer"
   swift_url: https://<aurl-address>/auth/v1.0/

Add the follwing line in vault.yml

.. code-block:: bash

   secrets
     swift_username: "XXXXXXXXXXX"
     swift_password: "YYYYYYYYYYY"

Deploy elasticsearch

.. code-block:: bash


   cchq <env> anisble-playbook deploy_db.yml --limit=elasticsearch

What Does Ansible do.
~~~~~~~~~~~~~~~~~~~~~


* Install the Plugin
* Restart ElasticSearch
* Create a snapshot repo
* Copy script to take snapshot
* Create a Cronjob

