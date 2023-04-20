#!/bin/bash

uptime_days=`uptime | awk '/days?/ {print $3; next}; {print 0}'`
echo $uptime_days

if  
	[[ $uptime_days -ge "90" ]] ;
then
       x=logger '[Maintenance]  Rebooting server as uptime is greater than or equal to ninety days' && reboot`
       $x;
fi
