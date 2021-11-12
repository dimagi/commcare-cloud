Ports Required for CommCareHQ
=============================

Below are the list of ports for various services required for running CommCareHQ.

.. list-table::
   :header-rows: 1

   * - Process
     - Port
     - Internal Access
     - External Access
     - Allow in Iptables? :sub:`Monolith Env`
     - Allow in Iptables? :sub:`Non-Monolith OR On-Premises Env`
     - Comments
   * - SSH
     - 22
     - yes
     - Restricted IPaddress
     - yes
     - yes
     - 
   * - Nginx https
     - 443
     - -
     - yes
     - yes
     - yes
     - 
   * - Nginx http
     - 80
     - -
     - yes
     - yes
     - yes
     - 
   * - Monolith Commcare
     - 9010
     - yes
     - no
     - no
     - depends
     - :sub:`routed via nginx `
   * - Formplayer
     - 8181
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - Kafka
     - 9092
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - Zookeeper
     - 2181
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - Redis
     - 6379
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - PostgreSQL PgBouncer
     - 5432 6432
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - RabbitMQ
     - 5672
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - ElasticSearch ES Cluster
     - 9200 9300
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - CouchDB
     - 5984 4369
     - yes
     - no
     - no
     - depends
     - :sub:`Accessible to private network`
   * - Celery port
     - 
     - 
     - no
     - no
     - 
     - 
   * - Mail/SMTP ports
     - 25 465 587
     - 
     - yes
     - no
     - 
     - 

