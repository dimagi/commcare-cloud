
=========================
Pillow Firefighting Guide
=========================

Background
----------

Pillows are background processes that consume changes from a change feed (e.g., from Kafka)
and run one or more processors (e.g., indexing into Elasticsearch, updating UCRs, etc).

Glossary
~~~~~~~~

**Pillow** - A group of processors that pull changes from a specific change feed (e.g., case-pillow)

**Processor** - A block of code that runs within a pillow for every change (e.g., save to elasticsearch)

**Process** - For every change feed we want to process changes from, we have pillow processes that get kicked off via something like `./manage.py run_ptop <specific-pillow>`

**Change Feed** - A queue of changes, either populated from couch or kafka (e.g., 'case-sql' topic in Kafka, database in couch)

**Topic** - represents a group of changes (e.g. case-sql, form-sql, etc) in Kafka

**Partition** -  subdivide a topic, and are useful when scaling in Kafka

Firefighting
------------

Symptoms of pillows being down:


* Data not appearing in reports, exports, or elasticsearch
* UCR or report builder reports behind
* `Datadog monitor <https://app.datadoghq.com/monitors#4013126?group=all&live=1d>`_

Resources:


* `graph of change feed activity <https://app.datadoghq.com/dash/256236/change-feeds?live=true&page=0&is_auto=false&from_ts=1518372763225&to_ts=1518459163225&tile_size=m&fullscreen=185100827>`_
* `Pillows documentation <https://commcare-hq.readthedocs.io/pillows.html>`_
* `Pillows overview and introduction <https://docs.google.com/presentation/d/1xgEZBer-FMUkeWutrTRcRbqKzVToK6mZvl0x2628BGY/edit#slide=id.p>`_

Confirm pillow lag
~~~~~~~~~~~~~~~~~~

Go to change feed dashboard and filter to impacted pillow

Confirm that all partitions for the selected pillow are impacted.
If only a few partitions are experiencing lag, it is likely that
one process for that pillow is backed up. In this case, we wait
for the issue to resolve itself. If all partitions appear to be experiencing
lag, move to diagnostic steps.

If you are unable to confirm pillow lag, but there are confirmed symptoms of
pillow lag, check for newly created pillow errors (see section under
diagnostic steps).

Diagnose the cause
~~~~~~~~~~~~~~~~~~

Check status of pillow processes
********************************

Run `cchq --control production service pillowtop status`

Make sure all processes for that pillow have a status of “RUNNING”

If any process is not running, do cchq --control <env> service pillowtop start –only=<pillow_name>

Run pillowtop status again to confirm pillow is now running. If it is not, check pillow logs for errors during startup. See “How to check logs”

Follow the instruction in readthedocs to check if the pillow is running. If it is not, check pillow logs for errors during startup. See https://dimagi.atlassian.net/wiki/spaces/saas/pages/edit-v2/3230597233#How-to-check-logs%3F 

Check load on impacted pillow
*****************************

See the load dashboard to correlate recent increases in load with increases in pillow lag.

If there is correlated load activity, is the activity ongoing or complete?

If ongoing, try to get more information about that activity

Is there an internal team member who has context on the project

If complete, try to estimate the time to recovery. How to estimate?

In either case, if we decide that waiting for the issue to resolve is not an option, see section on “Increasing pillow processing capacity”

Check pillow processing time
****************************

Use the average pillow processing time graph to determine if there is a steady increase in processing time that correlates with when the lag began. This can be due to the load being processed including multiple processors. For example, some cases will only need to be saved to elasticsearch, while others might also involve updating a UCR datasource and/or running a deduplication rule.

There aren’t necessarily followup actions to take here, but it is useful information.

Check pillow errors
*******************

Pillow errors can be found in:

Django Admin’s pillow errors. See if there is any new pillow error created recently.

Sentry by filtering by the pillow_name, eg. “pillow_name: case-pillow“

You should look for pillow errors that have been created recently. This could be an indication of a recent code change that is causing errors when processing changes in pillows. You can use the stacktrace available in each pillow error to diagnose and resolve the bug.

How to check logs?

TODO: move to read the docs

Before viewing logs, you need to determine which pillowtop machine contains the logs you are interested in.

You can find out which machine(s) a pillow process runs on by viewing the <env>/app_processes.yml

You can view logs in cloudwatch or directly on the machine

To see where logs live on the machine, run: cchq <env> service pillowtop logs



Resolve pillow issues
~~~~~~~~~~~~~~~~~~~~~

Increase pillow processing capacity
***********************************

make change to app-processes.yml

deploy by running update-supervisor-confs

TODO: link to read the docs

Decrease allowed global usage
*****************************

TODO: link to rate limiting docs
