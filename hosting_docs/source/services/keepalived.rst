
Keepalived
==========

`Keepalived <https://www.keepalived.org/doc/index.html>`_ is used for IP failover between two servers. It adds facilities for load balancing and high-availability to Linux-based infrastructures. Keepalived works on VRRP (Virtual Router Redundancy Protocol) protocol to make IPs highly available .

The VRRP protocol ensures that one of participating nodes is master. The backup node(s) listens for multicast packets from a node with a higher priority. If the backup node fails to receive VRRP advertisements for a period longer than three times of the advertisement timer, the backup node takes the master state and assigns the configured IP(s) to itself. In case there are more than one backup nodes with the same priority, the one with the highest IP wins the election.

Note: No fencing mechanism is available in Keepalived. If two participating nodes don't see each other,both will have the master state and both will carry the same IP(s).
In our Current infrastructure we are using it for couchdb proxy failover in ICDS environment.
We have plans to implement it more places where we have proxies setup.

Operational Notes:-
"""""""""""""""""""


#. 
   check keepalived status

   .. code-block::

       $ systemctl status keepalived

#. 
   know which one is the master
      Check the status/logs and you’ll see the log lines like this
     ``Sep 12 03:25:36 MUMGCCWCDPRDCDV09 Keepalived_vrrp[30570]: VRRP_Instance(VI_1) Entering BACKUP STATE``
     Check the virtual IP listed in ``/etc/keepalived/keepalived.conf``\ , verify if this IP address is assigned to the interface of the server.

#. 
   where are the logs

    Keepalived logs to journald 

   .. code-block::

       $ journalctl -u keepalived

#. 
   if we restart haproxy will that trigger a failover? ( only on master node)

   .. code-block::

       vrrp_script chk_service {           
           script "pgrep haproxy"  
           interval 2    
       }

From the config above it check for running process in every two second interval.if restart took longer than this, it will trigger failover


#. what's the process for taking haproxy offline e.g. during maintenance

   * If we are performing Maintenance on Backup Node

     * No Action

   * If we are performing Maintenance on Master Node

     * Stop haproxy and verify if Backup node is transitioned to master state from logs of Backup node (This is optional for just to be safe otherwise it should transition automatic once the haproxy stops on master node)

   * If we are Performing on both nodes at the same time.

     * Not much anyone can do 

Note:- All the nodes will go back to their desired state once the maintenance is over.
