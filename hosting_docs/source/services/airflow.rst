Airflow
=======

Usage in CommCare
-----------------

`Apache Airflow <https://airflow.apache.org/>`_ is a workflow tool that is used in some deployments
of CommCare to manage complex analytics workflows.


Migrating Airflow to a new host
===============================


#. Add the node information in inventory with ``airflow`` group assigned to it. (leave old host in ``airflow_scheduler`` group).
#. Run ``deploy-stack`` command. It will replicate all the jobs in the new node (except the scheduler).
#. Before moving the scheduler, stop the scheduler on the old node.

   #. Stop the process with ``supervisorctl``.
   #. Remove the supervisord config to prevent it from restarting.
   #. Reload supervisord: ``supervisorctl reread; supervisorctl update``

#. Replace host in ``airflow_scheduler`` group with the new host.
#. Run ``deploy-stack`` again (or just ``update-supervisor-confs``\ ) to create the configs for the scheduler on the new host.

   #. Make sure that the scheduler is running.

#. Make sure you can access the WEB UI on the new host and it has all the tasks listed
#. Remove the old node from inventory and decomission it.
