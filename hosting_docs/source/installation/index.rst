.. _deploy-commcarehq:

Deploy CommCareHQ
=================

This section has details on the following topics.

- How to deploy a CommCareHQ instance on one or more servers (also referred as install sometimes).
- Import data if you are migrating from another existing instance such as Dimagi's www.commcarehq.org or any other.
- A go-live checklist and :ref:`basic QA tests<new-env-qa>` to make sure everything is working well before making your instance live to the public.


Once you have understood what deployment option is most suitable for you using :ref:`deployment-options` guide and have all the :ref:`prerequisites <hosting-prereqs>` to deploy you can go ahead and deploy CommCareHQ! You can follow one of the deployment guides below depending on the type of deployment option that's suitable for you.

1. :ref:`quick-install`: This tutorial helps you install CommCareHQ on a single machine with an install wizard. Most of the install is done automatically with configuration set to sensible defaults. This is useful to quickly get started, test or preview what's involved in a working CommCareHQ environment.
2. :ref:`cchq-monolith-install`: This tutorial helps you install CommCareHQ on a single machine using :ref:`commcare-cloud <commcare-cloud>`, the command-line tool used to not only install CommCareHQ but also to manage a CommCareHQ instance through its entire life-cycle. This method gives you more visibility into installation process, more control and configuration options suitable to your own needs. This is the recommended way to setup a single machine production grade CommCareHQ instance.
3. :ref:`multi-server-install`: This set of tutorials and guides helps you install CommCareHQ across multiple servers for redundancy and better scalability. The installation process is done using :ref:`commcare-cloud <commcare-cloud>` same as above.


.. toctree::
   :caption: Table of Contents
   :maxdepth: 2

   /installation/monolith/1-easy_install_test
   /installation/monolith/2-install-prod
   /installation/multi-server/index
   /installation/troubleshooting
   /installation/new_environment_qa
   /installation/data-import/index
   /installation/multi-server/6-go-live-checklist.rst
