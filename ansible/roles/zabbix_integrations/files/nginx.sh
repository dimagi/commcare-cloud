#!/bin/bash
##################################################
# AUTHOR: Neo <netkiller@msn.com>
# WEBSITE: http://www.netkiller.cn
# Description：zabbix 通过 status 模块监控 nginx
# Note：Zabbix 3.2
# DateTime: 2016-11-22
# https://raw.githubusercontent.com/oscm/zabbix/master/nginx/
##################################################

HOST="localhost"
PORT="80"
stub_status=nginx_stub_status

function check() {
	/sbin/pidof nginx | wc -l
}

function active() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| grep 'Active' | awk '{print $NF}'
}
function accepts() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| awk NR==3 | awk '{print $1}'
}
function handled() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| awk NR==3 | awk '{print $2}'
}
function requests() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| awk NR==3 | awk '{print $3}'
}
function reading() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| grep 'Reading' | awk '{print $2}'
}
function writing() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| grep 'Writing' | awk '{print $4}'
}
function waiting() {
	/usr/bin/curl -s "http://$HOST:$PORT/${stub_status}/" 2>/dev/null| grep 'Waiting' | awk '{print $6}'
}

case "$1" in
	check)
		check
		;;
	active)
		active
		;;
	accepts)
		accepts
		;;
	handled)
		handled
		;;
	requests)
		requests
		;;
	reading)
		reading
		;;
	writing)
		writing
		;;
	waiting)
		waiting
		;;

	*)
		echo $"Usage $0 {check|active|accepts|handled|requests|reading|writing|waiting}"
		exit
esac
