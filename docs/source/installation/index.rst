.. _deploy-commcarehq:

Deploy CommCare HQ
==================

This section has details on the following topics.

- How to deploy a CommCare HQ instance on one or more servers (also referred as install sometimes).
- Import data if you are migrating from another existing instance such as Dimagi's www.commcarehq.org or any other using :ref:`migrate-project`.
- A :ref:`go-live-checklist` and :ref:`basic QA tests<new-env-qa>` to make sure everything is working well before making your instance live to the public.


Once you have understood what deployment option is most suitable for you using :ref:`deployment-options` guide and have all the :ref:`prerequisites <hosting-prereqs>` to deploy you can go ahead and deploy CommCare HQ! You can follow one of the deployment guides below depending on the type of deployment option that's suitable for you.

1. :ref:`quick-install`: This tutorial helps you install CommCare HQ on a single machine with an install wizard. Most of the install is done automatically with configuration set to sensible defaults. This is useful to quickly get started, test or preview what's involved in a working CommCare HQ environment.
2. :ref:`cchq-manual-install`: This tutorial helps you install CommCare HQ on a single machine or a small cluster using :ref:`prereqs/7-commcare-cloud:CommCare Cloud Deployment Tool`, the command-line tool used to not only install CommCare HQ but also to manage a CommCare HQ instance through its entire life-cycle. This method gives you more visibility into installation process, more control and configuration options suitable to your own needs. This is the recommended way to setup a multi machine production grade CommCare HQ instance.


.. toctree::
   :caption: Table of Contents
   :maxdepth: 2

   /installation/1-quick-monolith-install
   /installation/2-manual-install
   /installation/troubleshooting
   /installation/new_environment_qa
   /installation/migration/index
   /installation/go-live-checklist
