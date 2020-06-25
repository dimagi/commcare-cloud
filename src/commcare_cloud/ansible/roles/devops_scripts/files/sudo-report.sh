#!/bin/bash
#Filename: sudo-report.sh
#Description: Sudo attempts reporting tool with auth.log as input

SUDO_LOG=/tmp/sudo.$$.log

cp /dev/null $SUDO_LOG

for AUTHLOG in `ls /var/log/auth.log.1`
do

	#sudo success and Failure Reports
	zegrep "sudo: pam_unix|sudo: .*authentication failure|incorrect password attempts" $AUTHLOG >> $SUDO_LOG
done


#extract the users for successful sudo
sudo_success_users=$(cat $SUDO_LOG |grep 'session opened for user'|grep -oP '(?<=user )[^ ]*' | sort | uniq)
#extract the users for failed sudo
sudo_failed_users=$(cat $SUDO_LOG | grep 'incorrect password attempts'|grep -oP '(?<=USER=)[^ ]*' | sort | uniq)
#extract the users doing successful attempts
sudo_success_attempt=$(cat $SUDO_LOG |grep 'session opened for user'|grep -oP '(?<=by )[^ ]*' |sed 's/(.*//'| sort | uniq)
#extract the users doing failed attempts
sudo_failed_attempt=$(cat $SUDO_LOG |grep 'incorrect password attempts'|grep -oP '(?<=sudo:  )[^ ]*' | sort | uniq)
echo "#################################################################################"
echo " Below is the sudo attempt summary report created on - $(date)"
echo "#################################################################################"
# Print the heading
printf "%-12s|%-17s|%-17s|%-17s|%s\n" "Status" "SudoAttemptBy" "SudoTo" "Attempts" "Time"
for user in $sudo_success_users;
do
	for user_attempt in $sudo_success_attempt;
	do
	attempts_success=`grep 'session opened for user' $SUDO_LOG|grep "$user"|grep "$user_attempt"|wc -l`
	if [ $attempts_success -ne 0 ]
        then
		first_time=`grep 'session opened for user' $SUDO_LOG|grep "$user"|grep "$user_attempt"| head -1 | cut -c-16`
		time="$first_time"
		if [ $attempts_success -gt 1 ]
                then
	         last_time=`grep 'session opened for user' $SUDO_LOG|grep "$user"|grep "$user_attempt"|tail -1 | cut -c-16`
		 time="$first_time -> $last_time"
                fi
	printf "%-12s|%-17s|%-17s|%-17s|%s\n" "Success" "$user_attempt" "$user" "$attempts_success" "$time";
        fi
        done
done

for user in $sudo_failed_users;
do
	for user_attempt in $sudo_failed_attempt;
	do
	attempts_failed=`grep 'incorrect password attempts' $SUDO_LOG|grep "$user"|grep "$user_attempt"|wc -l`
	if [ $attempts_failed -ne 0 ]
        then
		first_time=`grep 'incorrect password attempts' $SUDO_LOG|grep "$user"|grep "$user_attempt"| head -1 | cut -c-16`
		time="$first_time"
		if [ $attempts_failed -gt 1 ]
		then
	         last_time=`grep 'incorrect password attempts' $SUDO_LOG|grep "$user"|grep "$user_attempt"| tail -1 | cut -c-16`
		 time="$first_time -> $last_time"
		fi
	printf "%-12s|%-17s|%-17s|%-17s|%s\n" "Failed" "$user_attempt" "$user" "$attempts_failed" "$time";
        fi
        done
done
rm -f $SUDO_LOG
