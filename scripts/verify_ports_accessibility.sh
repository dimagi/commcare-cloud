#!/bin/bash

### run script by passing argument in quotes 
## example: bash scriptname.sh "80 6379 3389 443"

ports=$1
restricted_ports=()
count=0
for p in ${ports}
do
  cmd=`nc -z 0.0.0.0 $p`
  if [ $p -eq 80 ] || [ $p -eq 443 ] && [ $? -eq 0 ]; then
    count=`expr $count + 1`
  else
	  restricted_ports+=("${p}")
  fi
done
if [ $count -eq 2 ]; then
	echo "All required ports are accessible"
else
	echo "All required ports are not accessible. Please check"
fi
echo -e "The following required ports aren't accessible: ${restricted_ports[*]} \n For more information visit ../docs/Commcare_Ports_information.xlsx"
