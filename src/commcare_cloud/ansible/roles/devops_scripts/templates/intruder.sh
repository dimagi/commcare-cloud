#!/bin/bash
#Filename: intruder_detect.sh
#Description: Intruder reporting tool with auth.log as input

FAILED_LOG=/tmp/failed.$$.log
SUCCESS_LOG=/tmp/success.$$.log
SUDO_LOG=/tmp/sudo.$$.log

cp /dev/null $FAILED_LOG
cp /dev/null $SUCCESS_LOG
cp /dev/null $SUDO_LOG

for AUTHLOG in `ls /var/log/auth.log*`
do

	# Collect the failed login attempts
        zegrep "Failed pass" $AUTHLOG >> $FAILED_LOG 

        # Collect the successful login attempts
        zegrep "Accepted password|Accepted publickey|keyboard-interactive" $AUTHLOG >> $SUCCESS_LOG
	
	#sudo success and Failure Reports
	zegrep "sudo: pam_unix|sudo: .*authentication failure" $AUTHLOG >> $SUDO_LOG
done

# extract the users who failed
failed_users=$(cat $FAILED_LOG | grep -oP '(?<=for )[^ ]*' | sort | uniq)

# extract the users who successfully logged in
success_users=$(cat $SUCCESS_LOG | grep -oP '(?<=for )[^ ]*' | sort | uniq)

#extract the users for successful sudo
sudo_success_users=$(cat $SUDO_LOG | grep ' sudo: pam_unix(sudo:session): session opened for user root' |grep -oP '(?<=by )[^ ]*' | sort | uniq)

#extract the users for failed sudo
sudo_failed_users=$(cat $SUDO_LOG | grep ' sudo: .*authentication failure' |grep -oP '(?<=user=)[^ ]*' | sort | uniq)

# extract the IP Addresses of successful and failed login attempts
failed_ip_list="$(egrep -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" $FAILED_LOG | sort | uniq)"
success_ip_list="$(egrep -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" $SUCCESS_LOG | sort | uniq)"

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

echo "#################################################################################"
echo " Below is the sudo attempt summary report "
echo "#################################################################################"
echo "There were $(grep -c ' sudo: pam_unix(sudo:session): session opened for user root' $SUDO_LOG) successful attempts to use sudo, and  $(grep -c ' sudo: .*authentication failure' $SUDO_LOG) were failed sudo attempts."
# Print the heading
printf "%-12s|%-17s|%s\n" "SudoAttempts" "User" "Attempts"
for user in $sudo_success_users;
do
	# Count successful sudo attempts by this user
	attempts=`cat $SUDO_LOG|grep ' sudo: pam_unix(sudo:session): session opened for user root'|grep -cw "$user"`
	printf "%-12s|%-17s|%-s\n" "Success" "$user" "$attempts"
done

for user in $sudo_failed_users;
do
	# Count Failed sudo attempts by this user
	attempts=`cat $SUDO_LOG|grep ' sudo: .*authentication failure'|grep -cw "$user"`
	printf "%-12s|%-17s|%-s\n" "Failed" "$user" "$attempts"
done

rm -f $FAILED_LOG
rm -f $SUCCESS_LOG
rm -f $SUDO_LOG
