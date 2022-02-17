How to Estimate Infrastructure Sizing
=====================================

CommCareHQ has a distributed architecture and each service can be scaled horizontally as more users are added to the project. Gradual scaling by adding resources as and when needed is the best way to scale a CommCareHQ project. This works well in cloud environments where resources can be procured instantaneously. But this doesn't work well when doing on-premise hosting where the infrastructure is bought one time exclusively for the project and there isn't a flexibility to gradually add resources. So, a way to estimate the infrastructure required for a given number of users becomes necessary.

Given that CommCareHQ is a complex distributed application, estimating infrastructure sizing for a given number of users is a complex task, and it's often more of an art than science as it requires keen observation of resource usage at different points of load for a given number of users.

commcare_resource_model
~~~~~~~~~~~~~~~~~~~~~~~

The infrastructure required to scale to a higher specific number of users can be obtained by examining the amount of resources (storage, RAM and CPU) that are getting used for a known current number of users. One most brute way to estimate the resource requirement would be to directly increase the hardware proportionate to the number of users. For e.g. if the system resources are all at their full capacity for 1000 users, to scale to 2000 users approximately a double amount of resources will be necessary.

But in practice, it will be more accurate to analyze the correlation between number of users and corresponding resource usage via load parameters such as form submissions, case creations, case updates, multimedia submissions and syncs etc that affect the resource usage more directly and then use these ratios to estimate for higher number of users. Such analysis could be done by examining the resource usage for a given time period. 

Once these load parameters and the relation to resource usage ratios are obtained, calculations can be done using a simple excel calculator to proportionately estimate the resources required for a higher number of users, but it would be complicated to manage/modify such an excel calculator. 

For this reason, we have developed a python based tool called `commcare_resource_model <http://github.com/dimagi/commcare_resource_model>`__. It takes a config file containing values for various user load and resource capacity parameters and ratios to estimate the resources required for higher user loads. Once the script is run for the given config, it will generate an excel file containing the resource estimates for a higher number of users.

One limitation of this tool or more correctly the limitation of the sizing methodology used in this tool is that the resource capacity must be known for each individual service. This is easy when each service is hosted on a different machine. When multiple services share a resource, it is not possible to estimate the resource capacity per each individual service. The tool can be still used for storage estimation as it is easy to examine the storage usage per each individual service as there are separate data directories for each service.

How to use commcare_resource_model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that commcare_resource_model can be used to estimate sizing only when a baseline usage and load data is available after CommCareHQ has been used for a given number of users. It can't be used for estimating sizing for a new project. To understand what infrastructure you need for a new project please refer to :ref:`sizing-buckets`.

The general process for using commcare_resource_model is below.

1. Install the commcare_resource_model python tool
2. Create a configuration file that specifies number of users to be scaled to, load and usage parameters from your existing environment
3. Run the script


The configuration file has three main sections that specifies the baseline usage and load of the system. Below are the three sections.


- **Usage section** Under this section all usage parameters such as number of users by date ranges and its correlation to load parameters (form submissions, case creations, case updates, multimedia submissions and syncs etc) can be listed. These numbers and ratios can be obtained by `project_stats_report <https://github.com/dimagi/commcare-hq/blob/master/corehq/apps/reports/management/commands/project_stats_report.py>`__ management command and also by examining the individual services, processes running one each VM.
- **Services section** for resource calculations for each service. This section can refer to one or more usage parameters from usage section which specifies the amount of usage that resource can handle.
- **Summary dates** The dates for which the resources need to be estimated.
- Additional parameters such as estimation_buffer, storage_display_unit etc are available.


Please refer to the `docs <https://github.com/dimagi/commcare_resource_model/blob/master/README.md>`__ for this tool to get an understanding of how to use this tool.
