
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

The majority of pillow issues manifest as pillow lag, which means that the pillow is not
up to date. The primary symptom is that data is not appearing or out of date in reports,
exports, UCRs, or elasticsearch.

For an overview of pillows, see `Pillows documentation <https://commcare-hq.readthedocs.io/pillows.html>`_

Confirm pillow lag
~~~~~~~~~~~~~~~~~~

1. Look at the metrics

   Go to `change feed dashboard <https://app.datadoghq.com/dashboard/ewu-jyr-udt/change-feeds-pillows?fromUser=false&refresh_mode=sliding&from_ts=1755710820633&to_ts=1755714420633&live=true>`_
   and filter to impacted pillow.
   Look at the `pilllow lag graph <https://app.datadoghq.com/dashboard/ewu-jyr-udt/change-feeds-pillows?fromUser=false&fullscreen_end_ts=1755714546214&fullscreen_paused=false&fullscreen_refresh_mode=sliding&fullscreen_section=overview&fullscreen_start_ts=1755710946214&fullscreen_widget=210889790&refresh_mode=paused&tpl_var_pillow%5B0%5D=case-pillow&from_ts=1751388427080&to_ts=1751396936000>`_.

2. Confirm that all partitions for the selected pillow are impacted. 
   
   If only a few partitions are experiencing lag, it is likely that
   one process for that pillow is backed up. In this case, we wait
   for the issue to resolve itself.

   If all partitions appear to be experiencing lag, move to diagnostic steps.

3. If you are unable to confirm pillow lag, but there are confirmed symptoms of
   pillow lag, check for newly created pillow errors (see `Check pillow errors`_).

Diagnose the cause
~~~~~~~~~~~~~~~~~~

Check status of pillow processes
********************************

1. Run `cchq --control <env> service pillowtop status`


2. Make sure all processes for that pillow have a status of “RUNNING”


3. If any process is not running, do `cchq --control <env> service pillowtop start –only=<pillow_name>`

   Run pillowtop status again to confirm pillow is now running. If it is not, check pillow logs for errors during startup. (See `Check pillow logs`_).

Check load on impacted pillow
*****************************

Check the `load dashboard <https://app.datadoghq.com/dashboard/hqu-2az-y2y/hq-load-forms-cases-ledgers-sms-ucr?fromUser=false&refresh_mode=sliding&from_ts=1749584335998&to_ts=1752003535998&live=true>`_
to determine if the pillow issues are caused by increased activity on a specific project.

If there is correlated load activity, is the activity ongoing or complete?

- If ongoing, try to get more information about that activity.
- If complete, try to estimate the time to recovery by understanding the throughput/rate of changes processed, and how many changes still need to be processed.

In either case, if we decide that waiting for the issue to resolve is not an option, see section on `Increase pillow processing capacity`_.

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

Check pillow logs
*****************

1. Before viewing logs, you need to determine which pillowtop machine contains the logs you are interested in.

   You can find out which machine(s) a pillow process runs on by viewing the `<env>/app_processes.yml`

2. You can view logs in cloudwatch or directly on the machine

   To see where logs live on the machine, run: `cchq <env> service pillowtop logs`



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
