Hardware resource requirements for CommCare HQ
==============================================

CommCare HQ is a complex software platform, composed of several parts
(application builder, report builder, databases, etc.). There is a range
of server configurations that can host all the parts of the CommCare HQ
software suite.

When determining what configuration to use, it is important to keep the
expected growth of the project in mind, in order to optimize costs and
limit possible service interruptions due to server management
operations. For example, if requisitioning more resources takes a while,
it is better to have some buffer -- more drive space, RAM, or cores than
necessary at first -- based on the expectation that by the time more
resources come available, they will have become necessary.

Alternatively, if you are hosting on a platform where requisitioning
resources is fast, or instant, buffer is less important, and it would
make more sense to optimise on resource costs.

Importantly, optimum resource management requires accurate resource
monitoring. For more details on this topic, see the CommCare Cloud
documentation on :ref:`label_datadog-for-monitoring`.

The following table summarizes common server configurations. This should
provide a basic understanding of the implications of scaling a project
to several thousands of users.

+---------------+-------------------------------------------------+-------------+----------------+-----------+----------------+
| Server        | Description                                     | Scalability | Infrastructure | Personnel | Risks          |
| Configuration |                                                 | (users)     | Cost           | Cost      |                |
+===============+=================================================+=============+================+===========+================+
| Single Server | A single server on which all the pieces of the  | < 1500      | Low            | Medium    | No built in    |
|               | CommCare HQ software suite are installed.       |             |                |           | redundancy.    |
|               |                                                 |             |                |           | Difficult to   |
|               |                                                 |             |                |           | transition to  |
|               |                                                 |             |                |           | larger cluster |
+---------------+-------------------------------------------------+-------------+----------------+-----------+----------------+
| Micro Cluster | Two servers running in parallel which provides  | < 3500      | Low            | Medium    |                |
|               | higher capacity than a single server as well as |             |                |           |                |
|               | better redundancy characteristics.              |             |                |           |                |
+---------------+-------------------------------------------------+-------------+----------------+-----------+----------------+
| Small Cluster | A five-server cluster, which the parts of       | < 15K       | Medium         | High      | Complex setup  |
|               | the CommCare HQ software suite are distributed  |             |                |           | requiring more |
|               | across.                                         |             |                |           | advanced       |
|               |                                                 |             |                |           | management     |
+---------------+-------------------------------------------------+-------------+----------------+-----------+----------------+
| Large Cluster | A cluster of more than five servers, which the  | > 15K       | High           | Very high | Very complex   |
|               | parts of the CommCare HQ software suite are     |             |                |           | setup and      |
|               | distributed across.                             |             |                |           | management     |
+---------------+-------------------------------------------------+-------------+----------------+-----------+----------------+

The number of users given in this table is a very rough guide. Every
project is different: Some have many users, each submitting a small
number of forms. Some have few users submitting many forms. Some
CommCare apps are simple, and servers do not need to spend a lot of
resources on syncing data and processing form submissions. Other apps
are complex, and the same number of users demand much more from the
servers. Some apps are used via the web interface exclusively, or have a
lot more multimedia, or submit large form attachments, shifting
requirements from some parts of CommCare HQ to other parts.

The recommended starting point for a project which is starting with a
small number of users but plans to scale beyond 1500 users, is the Micro
Cluster configuration. It gives the best combination of scalability and
cost.

By monitoring which services are using what resources, that data will
determine how to grow the cluster. For practical guidance on this topic,
see the CommCare Cloud documentation on
:ref:`label_datadog-for-monitoring`.


Virtualization
--------------

Where possible, virtual servers hosted by a Cloud Service Provider (CSP)
should always be preferred over physical servers. The reason for this is
that it makes maintenance and scaling of the cluster much simpler. It is
also generally more cost effective as the utilization of the resources
can be optimized and the burden of hardware management is removed.

It is recommended that virtualization be seriously considered for any
cluster that would require more than three physical servers.

Adding virtualization to physical servers makes it possible to utilize
the physical resources better, and makes certain maintenance tasks
simpler. However, installing and managing a virtualization layer
requires highly skilled personnel.


Single Server
-------------

This configuration is appropriate for projects with fewer than 1500
users, each user with an active case load of fewer that 10,000 cases,
and the project has no intention of growing.

Specific hardware guidelines can become outdated quickly. The
following specifications might be a reasonable suggestion:

* A mid-range server CPU
* At least 32 GB memory
* 2 TB SSD storage

Amazon EC2 t2.2xlarge and t3.2xlarge instances, configured with
sufficient General Purpose EBS storage, meet these CPU, memory and
storage specifications.

It is important to note that these suggestions are not appropriate for
all projects. Monitoring resource usage, and adapting server resources
accordingly, is crucial to meeting the needs of any project.

A Single Server configuration does not offer high availability. Server
failures can take the environment offline. If uptime is crucial for the
project, this is not a good option; a Micro Cluster configuration would
be more appropriate.


Micro Cluster
-------------

From a resource perspective, this configuration is two single servers.
But it opens up possibilities for how the environment is configured: One
server can be configured as fail-over for the services on the other
server. This is important for projects that need high availability.
Alternatively, services can be balanced across both servers. If the
project needs the resources of both servers combined, this sacrifices
high availability, but passes the initial hurdle to building a larger
cluster as a project grows.

This configuration is appropriate for small projects (projects with
fewer than 1500 users, each user with an active case load of fewer that
10,000 cases) that need high availability.

It is also appropriate as a starting configuration for small projects
that intend to grow to medium-sized projects, because it is more
difficult to turn a Single Server configuration into a cluster than it
is to extend a Micro Cluster configuration.

And it is appropriate for projects with fewer than about 3500 users.

Depending on the size of the project, this configuration has more range
in terms of resource specification. For a small project, without high
availability, resources for each machine could be lower than for a
Single Server configuration:

* A mid-range server CPU
* At least 16 GB memory
* 1 TB SSD storage

Amazon EC2 t2.xlarge and t3.xlarge instances, configured with sufficient
General Purpose EBS storage, meet these specifications.

For a small project which needs high availability, or for a medium-sized
project, twice the requirements of the Single Server configuration would
be appropriate:

* A mid-range server CPU
* At least 32 GB memory
* 2 TB SSD storage

Amazon EC2 t2.2xlarge and t3.2xlarge instances, configured with
sufficient General Purpose EBS storage, meet these specifications.


Small Cluster
-------------

A five-server cluster may be appropriate for projects with up to about
15,000 users. By this point virtualization should be considered
mandatory, for the sake of scalability, and in order to optimize
hardware resource usage.

If the size of the project allows, start with virtual machine instances
that are not at the highest resource specification. This allows for some
buffer to scale vertically (in other words, add more resources to the
same virtual machine) before the necessity to scale horizontally (add
more virtual machines).

Amazon EC2 t2.xlarge and t3.xlarge instances meet this description.

Storage requirements will be determined by the function of each server;
proxy and web servers will require less storage, database servers will
require more.

The level of skills, and the number of personnel, required to manage a
Small Cluster configuration are higher than for a Single Server or a
Micro Cluster.


Large Cluster
-------------

Depending on the nature of a project, typically as it approaches or
surpasses 15,000 users, it will require a server cluster of more than
five servers.

Recommendations are the same as for a Small Cluster configuration:

* Allow some room to scale virtual machines vertically before needing to
  scale horizontally

* Monitoring is crucial, because decisions must be guided by data

The level of skills, and the number of personnel, required to manage a
Large Cluster configuration are higher than for a Small Cluster.
