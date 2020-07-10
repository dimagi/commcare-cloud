#!/bin/bash

### run script by passing argument in quotes 
## example: bash verify_ports_accessibility.sh ip="IPaddres" ports="80 443 9300 6379"

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

address=${ip}
query_ports=${ports}
restricted_ports=()
count=0
for p in ${query_ports}
do
  cmd=`nc -z ${address} ${p}`
  result=$?
  if [ ${p} -eq 80 ] || [ ${p} -eq 443 ] && [ ${result} -eq 0 ]; then
    count=`expr $count + 1`
  else
    restricted_ports+=("${p}")
  fi
done

if [ ${count} -eq 2 ]; then
  echo "All required ports are accessible"
else
  echo "All required ports are not accessible. Please check"
fi
echo -e "The following required ports aren't accessible: ${restricted_ports[*]} \n For more information visit ../docs/Commcare_Ports_information.md"
