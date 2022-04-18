
Adding a new machine to a cluster
=================================


#. Add the machine to `inventory.ini <../commcare-cloud/env/index.md#inventoryini>`_
#. 
   Update the local known hosts

   .. code-block:: bash

       $ cchq <env> update-local-known-hosts

#. 
   For proxy, webworkers, celery, pillowtop run the following (this is the only step that modifies machines other than the new one):

   .. code-block:: bash

       # Register with the shared dir host whitelist
       # so the shared dir host allows the new machine to mount the shared dir
       cchq <env> ansible-playbook deploy_shared_dir.yml --limit shared_dir_host

#. 
   Deploy stack

   .. code-block:: bash

       cchq --control <env> deploy-stack --first-time --limit <new host>

    If it fails part way through for transient reasons (network issue, etc.) and running again fails with SSH errors, that means it has already switched over from the factory SSH setup to the standard SSH setup we use, and you can no longer use --first-time. To resume, run the following instead

   .. code-block:: bash

       $ cchq --control <env> deploy-stack --skip-check --skip-tags=users --limit <new host>  # Only run this to resume if the above fails part way through

#. 
   For anything that has commcarehq code you then have to deploy.

    To make sure all the machines are running the same version of commcare otherwise the machine that was just provisioned has the latest, and everything else has an old version.

   .. code-block:: bash

       # this is important in case there was drift between the branch where new setup was run and master
       # it also makes sure that all machines have the same settings
       $ cchq <env> update-config
       $ cchq <env> deploy

#. 
   If your change involves shuffling processes around in app-process.yml or otherwise requires updating supervisor confs on machines other than the new one, run

    This updates the supervisor configurations (text files) on the relevant machine so that supervisor knows what processes should be running.

   .. code-block:: bash

       $ cchq <env> update-supervisor-confs
