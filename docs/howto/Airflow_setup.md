## Migrating Airflow
1. Add the node information in inventory with `airflow` group assigned to it. (leave old host in airflow_scheduler group)
2. Remove the old node from `airflow ` group.The inventory should not have more than one node in `airflow` group.
3. `deploy-stack` command will replicate all the jobs in the new node.
4. At this point we have two nodes with replicated job on both nodes. Before proceeding stop the scheduler  with `supervisorctl` on old  node.
5. Replace host in airflow_scheduler group with the new host
6. Run `deploy-stack` again (or just `update-supervisor-confs`) to create the configs for the scheduler on the new host.
7. Make sure you can access the `WEB UI` and it has all the task to the new machines
8. Remove the old node from inventory.
