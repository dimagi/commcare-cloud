#!/bin/bash
#Filename: intruder_detect.sh
#Description: Intruder reporting tool with auth.log as input

FAILED_LOG=/tmp/failed.$$.log
SUCCESS_LOG=/tmp/success.$$.log

cp /dev/null $FAILED_LOG
cp /dev/null $SUCCESS_LOG

for AUTHLOG in `ls /var/log/auth.log.1`
do

	# Collect the failed login attempts
        zegrep "Failed pass" $AUTHLOG >> $FAILED_LOG 

        # Collect the successful login attempts
        zegrep "Accepted password|Accepted publickey|keyboard-interactive" $AUTHLOG >> $SUCCESS_LOG
	
done

# extract the users who failed
failed_users=$(cat $FAILED_LOG | grep -oP '(?<=for )[^ ]*' | sort | uniq)

# extract the users who successfully logged in
success_users=$(cat $SUCCESS_LOG | grep -oP '(?<=for )[^ ]*' | sort | uniq)

# extract the IP Addresses of successful and failed login attempts
failed_ip_list="$(egrep -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" $FAILED_LOG | sort | uniq)"
success_ip_list="$(egrep -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" $SUCCESS_LOG | sort | uniq)"

echo "#################################################################################"
echo " Below is the Login attempt summary report created on - $(date)"
echo "#################################################################################"

# Print the heading
printf "%-10s|%-10s|%-10s|%-15s|%-15s|%s\n" "Status" "User" "Attempts" "IP address" "Host" "Time range"

# Loop through IPs and Users who failed.

for ip in $failed_ip_list;
do
  for user in $failed_users;
    do
    # Count failed login attempts by this user from this IP
    attempts=`grep $ip $FAILED_LOG | grep " $user " | wc -l`

    if [ $attempts -ne 0 ]
    then
      first_time=`grep $ip $FAILED_LOG | grep " $user " | head -1 | cut -c-16`
      time="$first_time"
      if [ $attempts -gt 1 ]
      then
        last_time=`grep $ip $FAILED_LOG | grep " $user " | tail -1 | cut -c-16`
        time="$first_time -> $last_time"
      fi
      HOST=$(host $ip 8.8.8.8 | tail -1 | awk '{ print $NF }' )
      printf "%-10s|%-10s|%-10s|%-15s|%-15s|%-s\n" "Failed" "$user" "$attempts" "$ip"  "$HOST" "$time";
    fi
  done
done

for ip in $success_ip_list;
do
  for user in $success_users;
    do
    # Count successful login attempts by this user from this IP
    attempts=`grep $ip $SUCCESS_LOG | grep " $user " | wc -l`

    if [ $attempts -ne 0 ]
    then
      first_time=`grep $ip $SUCCESS_LOG | grep " $user " | head -1 | cut -c-16`
      time="$first_time"
      if [ $attempts -gt 1 ]
      then
        last_time=`grep $ip $SUCCESS_LOG | grep " $user " | tail -1 | cut -c-16`
        time="$first_time -> $last_time"
      fi
      HOST=$(host $ip 8.8.8.8 | tail -1 | awk '{ print $NF }' )
      printf "%-10s|%-10s|%-10s|%-15s|%-15s|%-s\n" "Success" "$user" "$attempts" "$ip"  "$HOST" "$time";
    fi
  done
done

rm -f $FAILED_LOG
rm -f $SUCCESS_LOG
