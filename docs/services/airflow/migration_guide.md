# Migrating Airflow to a new host
1. Add the node information in inventory with `airflow` group assigned to it. (leave old host in `airflow_scheduler` group).
2. Run `deploy-stack` command. It will replicate all the jobs in the new node (except the scheduler).
4. Before moving the scheduler, stop the scheduler on the old node.
   1. Stop the process with `supervisorctl`.
   2. Remove the supervisord config to prevent it from restarting.
   3. Reload supervisord: `supervisorctl reread; supervisorctl update`
5. Replace host in `airflow_scheduler` group with the new host.
6. Run `deploy-stack` again (or just `update-supervisor-confs`) to create the configs for the scheduler on the new host.
   1. Make sure that the scheduler is running.
7. Make sure you can access the WEB UI on the new host and it has all the tasks listed
8. Remove the old node from inventory and decomission it.
