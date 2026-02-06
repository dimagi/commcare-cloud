
Upgrading CouchDB
=================

Step-by-step guide to upgrade CouchDB nodes. Repeat these steps for all couch nodes in all environments.

Step 1: Set Variables
---------------------

Set the following variables on both **Local** and **Control** machines.

.. code-block:: bash

    couch_a1=<ip_address_of_couch_a1>
    couch_a2=<ip_address_of_couch_a2>
    couch_b1=<ip_address_of_couch_b1>

    username=$(cchq <env> secrets view COUCH_USERNAME)
    password=$(cchq <env> secrets view COUCH_PASSWORD)

Step 2: Update and Verify Variables
-----------------------------------

Update the following variables accordingly and verify that they are correct on both **Local** and **Control** machines.

.. code-block:: bash

    couch_instance_id="<instance_id>"
    node_to_upgrade=$couch_a1
    node_name_to_upgrade="couch_a1"
    couch_coordinator=$couch_b1
    couch_volume_id="<volume_id>"
    alb_target_arn='<alb_target_arn>'

Step 3: Take Node Out of ALB
----------------------------

**[Local Machine]** Deregister target from ALB.

.. code-block:: bash

    aws elbv2 deregister-targets --target-group-arn ${alb_target_arn} --targets Id=${couch_instance_id} --profile <aws_profile>

Verify node is removed:

.. code-block:: bash

    aws elbv2 describe-target-health --target-group-arn ${alb_target_arn} --targets Id=${couch_instance_id} --profile <aws_profile> --no-cli-pager --output=text

Step 4: Stop Couch Pillows
--------------------------

**[Control Machine]** Stop the pillows.

.. code-block:: bash

    cchq <env> service pillowtop stop --only=AppDbChangeFeedPillow,DefaultChangeFeedPillow,DomainDbKafkaPillow,UserGroupsDbKafkaPillow

Step 5: Maintenance Mode
------------------------

**[Control Machine]** Put couch node in maintenance mode.

.. code-block:: bash

    curl -X PUT -H "Content-type: application/json" http://${username}:${password}@${couch_coordinator}:15984/_node/couchdb@${node_to_upgrade}/_config/couchdb/maintenance_mode -d '"true"'

Verify node is in maintenance:

.. code-block:: bash

    curl http://${username}:${password}@${node_to_upgrade}:15984/_up

Step 6: Stop Couch Node
-----------------------

**[Control Machine]** Stop the couch node serivce.

.. code-block:: bash

    cchq <env> run-shell-command ${node_name_to_upgrade} 'systemctl stop monit && systemctl stop couchdb' -b

Step 7: Create Snapshot
-----------------------

**[Local Machine]** Create a snapshot of the data volume.

.. code-block:: bash

    aws ec2 create-snapshot \
      --volume-id ${couch_volume_id} \
      --description "Snapshot of data-vol-${node_name_to_upgrade}-<env>" \
      --tag-specifications "ResourceType=snapshot,Tags=[{Key=Name,Value=data-vol-${node_name_to_upgrade}-<env>},{Key=SnapshotTag,Value=data-vol-${node_name_to_upgrade}-<env>},{Key=created_for,Value=couch_upgrade}]" \
      --profile <aws_profile> \
      --output text \
      --no-cli-pager

Wait for snapshot to be created:

.. code-block:: bash

    aws ec2 describe-snapshots --profile <aws_profile> --snapshot-ids snap-<> --no-cli-pager

Step 8: Deploy CouchDB
----------------------

**[Control Machine]** Run `deploy_couchdb2.yml`.

.. code-block:: bash

    git fetch && git checkout <branch_name>
    cchq <env> ap deploy_couchdb2.yml --limit=${node_name_to_upgrade} --branch='<branch_name>'

Step 9: Verification
--------------------

**[Control Machine]** Verify the version and authentication.

.. code-block:: bash

    curl -s http://${node_to_upgrade}:15984/ | jq .version

    # Test authentication (passwords will be rehashed)
    curl "http://${username}:${password}@${node_to_upgrade}:15984/_all_dbs"
    curl http://${username}:${password}@${node_to_upgrade}:15984/_membership

Step 10: Add Node Back to ALB
-----------------------------

**[Local Machine]** Register target back to ALB.

.. code-block:: bash

    aws elbv2 register-targets --target-group-arn ${alb_target_arn} --targets Id=${couch_instance_id} --profile <aws_profile>

Verify node is added:

.. code-block:: bash

    aws elbv2 describe-target-health --target-group-arn ${alb_target_arn} --targets Id=${couch_instance_id} --profile <aws_profile> --no-cli-pager --output=text

Step 11: Remove Maintenance Mode
--------------------------------

**[Control Machine]** Remove node from maintenance mode.

.. code-block:: bash

    curl -X PUT -H "Content-type: application/json" http://${username}:${password}@${couch_coordinator}:15984/_node/couchdb@${node_to_upgrade}/_config/couchdb/maintenance_mode -d '"false"'

Verify node maintenance status:

.. code-block:: bash

    curl http://${username}:${password}@${node_to_upgrade}:15984/_up

Step 12: Start Couch Pillows
----------------------------

**[Control Machine]** Start the pillows.

.. code-block:: bash

    cchq <env> service pillowtop start --only=AppDbChangeFeedPillow,DefaultChangeFeedPillow,DomainDbKafkaPillow,UserGroupsDbKafkaPillow
