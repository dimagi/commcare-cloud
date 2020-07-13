#!/bin/bash

### run script by passing argument in quotes 
## example: bash verify_ports_accessibility.sh ip="IPaddres" ports="80 443 9300 6379"

# reading arguments
for args in "$@"
do

    key=$(echo $args | cut -f1 -d=)
    value=$(echo $args | cut -f2 -d=)   

    case "$key" in
            ip)       ip=${value} ;;
            ports)    ports=${value} ;;     
            *)   
    esac    

done

# retriving port information with static values
function get_port_desc()
{
  port=$1
  local AllPorts="SSH:22 https:443 http:80 Monolith_Commcare:9010 Formplayer:8181 Kafka:9092 Zookeeper:2181 Redis:6379 PostgreSQL:5432 PgBouncer:6432 RabbitMQ:5672 ElasticSearch:9200 ES_Cluster:9300 CouchDB:5984,4369 Celery_port:5555 Mail/SMTP:25,465,587"
  desc=${port}
  for pi in ${AllPorts} ;
  do
     if [[ "$pi" =~ .*"${port}".* ]]; then
          desc="${pi}"
     fi
  done

  #returns given #port if not found the port desc
  echo ${desc}
}

# -- 

address=${ip}
query_ports=${ports}
restricted_ports=()
portdesc=()
count=0
for p in ${query_ports}
do
  cmd=`nc -z ${address} ${p}`
  result=$?
  if [ ${p} -eq 80 ] || [ ${p} -eq 443 ] && [ ${result} -eq 0 ]; then
    count=`expr $count + 1`
  else
    #restricted_ports+=("${p}")
    restricted_ports+="$(get_port_desc ${p}) \n"
  fi
done

if [ ${count} -eq 2 ]; then
  echo "All required ports are accessible"
else
  echo "All required ports are not accessible. Please check"
fi

echo -e "The following required ports aren't accessible:\n${restricted_ports[*]} For more information visit ../docs/Commcare_Ports_information.md"
