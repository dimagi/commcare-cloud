# RiakCS migration from NIC to TCL

## Special Notes

The admin and secret keys for Riak need to match up between the old and new cluster.
On the new cluster:

* Change them in /etc/riak-cs/riak-cs.conf and in the vault file to match old cluster
* Deploy riak
* Deploy localsettings

## Migration process

1. Stop all Riak processes

    ```
    $ cchq icds-new service riakcs stop
    $ cchq icds-cas service riakcs stop
    ```

2. Copy data

    Clear data directores on new cluster
    ```
    $ cchq icds-cas run-shell-command riakcs "rm -rf /opt/data/riak/*" -b
    ```

    Run copy commands
    ```
    cchq icds-cas copy-files environments/icds-cas/migrations/riak-files.yml prepare
    cchq icds-cas copy-files environments/icds-cas/migrations/riak-files.yml copy
    cchq icds-cas copy-files environments/icds-cas/migrations/riak-files.yml cleanup
    ```

3. Re-IP first node

    ```
    $ riak-admin reip riak-10@10.247.164.48 riak-100@100.71.184.33
    ```

4. Start node
    ```
    service riak start
    ```

5. Mark all other nodes as down
    ```
    $ riak-admin down riak-10@10.247.164.13
    $ riak-admin down riak-10@10.247.164.18
    $ riak-admin down riak-10@10.247.164.39
    $ riak-admin down riak-10@10.247.164.49
    $ riak-admin down riak-10@10.247.164.50
    $ riak-admin down riak-10@10.247.164.51
    $ riak-admin down riak-10@10.247.164.53
    $ riak-admin down riak-10@10.247.164.54
    $ riak-admin down riak-10@10.247.164.55
    ```

6. Check member status to verify all down except for first node

    ```
    $ riak-admin member-status
    
    ================ Membership ============
    Status     Ring        Pending    Node
    -----------------------------------------------------------
    valid       X%      --      'riak-100@100.71.184.33'
    down        X%      --      'riak-10@10.247.164.13'
    down        X%      --      'riak-10@10.247.164.18'
    down        X%      --      'riak-10@10.247.164.39'
    down        X%      --      'riak-10@10.247.164.49'
    down        X%      --      'riak-10@10.247.164.50'
    down        X%      --      'riak-10@10.247.164.51'
    down        X%      --      'riak-10@10.247.164.53'
    down        X%      --      'riak-10@10.247.164.54'
    down        X%      --      'riak-10@10.247.164.55'
    ------------------------------------------------------------
    Valid:1 / Leaving:0 / Exiting:0 / Joining:0 / Down:9
    
    ```

7. Ensure new node is listed as the claimant by running 
    ```
    $ riak-admin ring-status
    
    ================== Claimant =============
    Claimant:  'riak-100@100.71.184.33'
    Status:     up
    Ring Ready: true
    
    ================== Ownership Handoff ============
    No pending changes.
    
    ================== Unreachable Nodes =============
    All nodes are up and reachable
    ```

8. Rename ring dir on all other nodes
    
    ```
    $ cchq icds-cas run-shell-command riakcs -b "mv {{ encrypted_root }}/riak/ring {{ encrypted_root }}/ring.bak" --limit 'all:!100.71.184.33'
    ```

9. Start other nodes

    ```
    $ cchq icds-cas run-shell-command riakcs -b "service riak start" --limit 'all:!100.71.184.33'
    ```

10. Join other nodes to cluster (run from each other node)

    ```
    $ cchq icds-cas run-shell-command riakcs -b "riak-admin cluster join riak-100@100.71.184.33" --limit 'all:!100.71.184.33'
    ```

11. Check cluster plan to see that all new nodes are registered as joining

    ```
    $ riak-admin cluster plan
    ```

12. Force replace each node with its old node name.

    ```
    $ riak-admin cluster force-replace riak-10@10.247.164.49 riak-100@100.71.184.43
    $ riak-admin cluster force-replace riak-10@10.247.164.50 riak-100@100.71.184.13
    $ riak-admin cluster force-replace riak-10@10.247.164.51 riak-100@100.71.184.44
    $ riak-admin cluster force-replace riak-10@10.247.164.18 riak-100@100.71.184.50
    $ riak-admin cluster force-replace riak-10@10.247.164.53 riak-100@100.71.184.37
    $ riak-admin cluster force-replace riak-10@10.247.164.54 riak-100@100.71.184.48
    $ riak-admin cluster force-replace riak-10@10.247.164.55 riak-100@100.71.184.40
    $ riak-admin cluster force-replace riak-10@10.247.164.39 riak-100@100.71.184.46
    $ riak-admin cluster force-replace riak-10@10.247.164.13 riak-100@100.71.184.35
    ```

13. Check cluster plan

    ```
    $ riak-admin cluster plan
    
    =============== Staged Changes ===============
    Action         Details(s)
    ----------------------------------------------------------
    force-replace  'riak-10@10.247.164.49' with 'riak-100@100.71.184.43'
    force-replace  'riak-10@10.247.164.50' with 'riak-100@100.71.184.13'
    force-replace  'riak-10@10.247.164.51' with 'riak-100@100.71.184.44'
    force-replace  'riak-10@10.247.164.18' with 'riak-100@100.71.184.50'
    force-replace  'riak-10@10.247.164.53' with 'riak-100@100.71.184.37'
    force-replace  'riak-10@10.247.164.54' with 'riak-100@100.71.184.48'
    force-replace  'riak-10@10.247.164.55' with 'riak-100@100.71.184.40'
    force-replace  'riak-10@10.247.164.39' with 'riak-100@100.71.184.46'
    force-replace  'riak-10@10.247.164.13' with 'riak-100@100.71.184.35'
    join           'riak-100@100.71.184.43'
    join           'riak-100@100.71.184.13'
    join           'riak-100@100.71.184.44'
    join           'riak-100@100.71.184.50'
    join           'riak-100@100.71.184.37'
    join           'riak-100@100.71.184.48'
    join           'riak-100@100.71.184.40'
    join           'riak-100@100.71.184.46'
    join           'riak-100@100.71.184.35'
    ----------------------------------------------------------
    
    WARNING: All of 'riak-100@100.71.184.43' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.13' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.44' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.50' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.37' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.48' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.40' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.46' replicas will be lost
    WARNING: All of 'riak-100@100.71.184.35' replicas will be lost
    
    NOTE: Applying these changes will result in 1 cluster transition
    
    ##########################################################
                             After cluster transition 1/1
    ##########################################################
    
    =============== Membership ===============
    Status     Ring    Pending    Node
    ----------------------------------------------------------
    valid        X%      --      'riak-100@100.71.184.33'
    valid        X%      --      'riak-100@100.71.184.43'
    valid        X%      --      'riak-100@100.71.184.13'
    valid        X%      --      'riak-100@100.71.184.44'
    valid        X%      --      'riak-100@100.71.184.50'
    valid        X%      --      'riak-100@100.71.184.37'
    valid        X%      --      'riak-100@100.71.184.48'
    valid        X%      --      'riak-100@100.71.184.40'
    valid        X%      --      'riak-100@100.71.184.46'
    valid        X%      --      'riak-100@100.71.184.35'
    ----------------------------------------------------------
    Valid:10 / Leaving:0 / Exiting:0 / Joining:0 / Down:0
    
    Partitions reassigned from cluster changes: 51
      XX reassigned from 'riak-10@10.247.164.49' to 'riak-100@100.71.184.33'
    ....
    ```

14. Commit plan

    ```
    $ riak-admin cluster commit
    ```

15. Check member status

    ```
    $ riak-admin member-status
    
    ================= Membership =================
    Status       Ring       Pending    Node
    -----------------------------------------------------------
    valid        X%      --      'riak-100@100.71.184.33'
    valid        X%      --      'riak-100@100.71.184.43'
    valid        X%      --      'riak-100@100.71.184.13'
    valid        X%      --      'riak-100@100.71.184.44'
    valid        X%      --      'riak-100@100.71.184.50'
    valid        X%      --      'riak-100@100.71.184.37'
    valid        X%      --      'riak-100@100.71.184.48'
    valid        X%      --      'riak-100@100.71.184.40'
    valid        X%      --      'riak-100@100.71.184.46'
    valid        X%      --      'riak-100@100.71.184.35'
    -----------------------------------------------------------
    Valid:10 / Leaving:0 / Exiting:0 / Joining:0 / Down:0
    ```

16. Start RiakCS
    
    ```
    $ cchq icds-cas service riakcs start
    ```
