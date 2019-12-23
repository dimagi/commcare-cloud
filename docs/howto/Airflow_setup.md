## Migrating Airflow
1. Add the node information in inventory with `airflow` group assigned to it.
2. Remove the old node from `airflow ` group.The inventory should not have more than one node in `airflow` group.
3. `deploy-stack` command will replicate all the jobs in the new node.
4. At this point we have two nodes with replicated job on both nodes. Before proceeding stop the process with `supervisorctl` on all the node.
5. Run `cchq <env> update-supervisor-conf` 
6. Make sure you can access the `WEB UI` and it has all the task to the new machines
7. Remove the old node from inventory.
