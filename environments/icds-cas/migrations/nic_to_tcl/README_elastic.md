# Elasticsearch migration from NIC to TCL

1. Turn off all nodes in old cluster and new cluster.

    ```
    $ cchq icds service elasticsearch-classic stop
    $ cchq icds-cas service elasticsearch-classic stop
    ```

2. Clear data directores on new cluster
   
    ```
    $ cchq icds-cas run-shell-command elasticsearch "rm -rf /opt/data/elasticsearch-1.7.6/*" -b
    ```

3. Copy data

    ```
    cchq icds-cas copy-files environments/icds-cas/migrations/elastic-files.yml prepare
    cchq icds-cas copy-files environments/icds-cas/migrations/elastic-files.yml copy
    cchq icds-cas copy-files environments/icds-cas/migrations/elastic-files.yml cleanup
    ```

4. Turn on new elasticsearch nodes

    ```
    $ cchq icds-cas service elasticsearch-classic start
    ```
    
5. Check cluster health
    ```
    curl http://100.71.184.7:9200/_cluster/health
    ```
    
    Check log files for any errors
    
    ```
    tail -f /opt/data/elasticsearch-1.7.6/logs/*.log
    ```
    
    Check using ES HEAD that cluster loads correctly
    Check stats to make sure doc counts match 
    
    ```
    http://10.247.164.15:9200/_stats 
    http://100.71.184.7:9200/_stats 
    ```
