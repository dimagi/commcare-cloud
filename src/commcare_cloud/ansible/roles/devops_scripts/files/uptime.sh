#!/bin/bash

#uptime_days=`uptime | awk '/days?/ {print $3; next}; {print 0}'`
#echo $uptime_days

#if
	#[[ $uptime_days -ge "90" ]] ;
#then
       #x=logger '[Maintenance]  Rebooting server as uptime is greater than or equal to ninety days' && reboot`
       #$x;
#fi

#!/bin/bash

maintenance_time={{ maintenance_time }}
current_time=$(uptime | awk '{print $1}';)
uptime_days=`uptime | awk '/days?/ {print $3; next}; {print 0}'`
echo $uptime_days

if
	[[ $uptime_days -ge "90" ]] && [ $current_time = $maintenance_time ];
then
       x=logger '[Maintenance]  Rebooting server as uptime is greater than or equal to ninety days' && reboot`
       $x;
fi
