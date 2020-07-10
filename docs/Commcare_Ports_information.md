|Process|Port|Internal<br>Access|External<br>Access|Allow in Iptables?<br><sub>Monolith Env</sub>|Allow in Iptables?<br><sub>Non-Monolith OR<br>On-Premises Env</sub>|Comments|
|:--|:--|:--|:--|:--|:--|:--|
|SSH|22|yes|Restricted<br>IPaddress|yes|yes||
|Nginx https| 443 |-|yes|yes|yes|           |
|Nginx http| 80 |-|yes|yes|yes||
|Monolith Commcare|9010|yes|no|no|depends |<sub>routed via nginx </sub>|
|Formplayer|8181|yes|no|no|depends|<sub>Accessible to private network</sub>|
|Kafka|9092|yes|no|no|depends|<sub>Accessible to private network</sub>|
|Zookeeper|2181|yes|no|no|depends|<sub>Accessible to private network</sub>|
|Redis|6379|yes|no|no|depends|<sub>Accessible to private network</sub>|
|PostgreSQL<br>PgBouncer|5432<br>6432|yes|no|no|depends|<sub>Accessible to private network</sub>|
|RabbitMQ   | 5672|  yes|  no |  no   |  depends |<sub>Accessible to private network</sub>|
|ElasticSearch <br> ES Cluster | 9200 <br> 9300 |  yes|  no |  no   |  depends |<sub>Accessible to private network</sub>|
|CouchDB    | 5984<br>4369  |  yes|  no |  no   |  depends |<sub>Accessible to private network</sub>|
|Celery port          |      |    |  no |  no   |          |           |
|Mail/SMTP ports      |           |    |  yes         |  no   |          |           |