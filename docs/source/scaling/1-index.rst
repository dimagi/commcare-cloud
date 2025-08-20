.. _how-to-scale:

How to Scale
============

This section contains guides on how to test your CommCare HQ instance's performance and how to estimate sizing for higher number of users using a tool called `commcare_resource_model <http://github.com/dimagi/commcare_resource_model>`_.

The hardware requirements required for instances under 15,000 mobile users is given at :ref:`prereqs/5-requirements:Hardware requirements and Deployment Options`. This section is intended to provide information on how to scale CommCare HQ for projects going beyond 15,000 mobile users.


.. TODO:
   * /scaling/2-webworkers
   * /scaling/3-postgres
   * /scaling/4-redis
   * /scaling/5-elasticsearch
   * /scaling/6-sizing-buckets

.. toctree::
   :maxdepth: 4

   /scaling/perfomance-test
   /scaling/sizing
