.. _hardware-management:

Managing Hardware and the Physical Environment
==============================================

Dimagi recommends outsourcing the maintenance of hardware and the
physical hosting environment to a cloud service provider. For some
projects, for a range of possible reasons or on balance of factors,
that may not be desirable, or an option.


Third-party documents
---------------------

Perhaps the canonical document on managing hardware, within the
wholistic context of managing a data center, is the BICSI International
Standard,
`ANSI/BICSI 002, Data Center Design and Implementation Best Practices <https://www.bicsi.org/standards/available-standards-store/single-purchase/ansi-bicsi-002-2019-data-center-design>`_.
At the time of writing, the latest revision is BICSI 002-2019. At 500
pages long, it is comprehensive. A digital copy costs $525.

Samples, and `a presentation <https://www.bicsi.org/docs/default-source/conference-presentations/2017-fall/using-the-ansi-bicsi-002.pdf>`_ based on the content are available free
online. The presentation will give a good impression of the detailed
thinking required to maintain a secure and reliable hosting environment.


Costs for maintaining a self-hosted production environment
----------------------------------------------------------

These are long-term (year-over-year) costs that should be considered
when determining the price of a “fixed cost” option, where servers are
procured specifically for the project.

Purchasing production server equipment is quite different from
purchasing personal computing equipment. Since servers will run
continuously, and operations need to be available within predictable
prices, server hardware cost is built around warranty and license
life-cycles for equipment, where the warranty will ensure that the
hardware continues to deliver over the time period.

For this example, we will presume a representative 16-Core 64GB server
with a base cost of about $5,000, which generally fulfills the
requirements of a monolith server. We will presume that the project will
run for a five year period for representative total costs.


Hardware Replacement and Warranty
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The expected lifespan for reliable server equipment in a data center is
3-5 years, which depends on many factors but can be lowered depending on
the quality of power supplied and things like appropriate cooling and
ventilation.

Traditionally a team without a significant stock of replacement
components will purchase servers with a comprehensive warranty plan with
the expectation that they will purchase new equipment when the warranty
expires.

"Next business day" (v. 24/7 which is more expensive) support for 3 and
5 years costs $900 and $3000 respectively, making the year to year cost
for the server:

================   =====   ==================   ===========
Years in Service   Base    Warranty / Support   Yearly Cost
================   =====   ==================   ===========
3                  $5000   $900                 $1,966
5                  $5000   $3000                $1,600
================   =====   ==================   ===========


Storage
^^^^^^^

When made available from a vendor, high durability block storage is made
available at a fixed price. This storage will be robust against failures
in individual hardware disks transparently without intervention. Without
high durability storage, it should be expected that disk failure will
result in the need to restore the system in full from backup (and with
the loss of data in between the backup) at least once in a three year
period.

When block storage isn't available, high durability storage must be
created and maintained manually. This requires available backup disks, a
software or hardware SAN appliance to produce high durability virtual
storage, and a maintenance plan for replacing disks urgently.

Hard drive warranties are generally around 3 years, and producing 1TB of
storage would generally require purchasing 1.5TB worth of disks during
that period, since 33% will be lost to the redundant storage layer, and
1 additional disk needs to remain available to replace a faulted disk.

A 500GB server disk from HP is ~$300, making the year-to-year cost for
1TB of storage (including replacement) around $300 per year (3 years per
disk, 3 disks in use at once for 1TB of storage).

=============  =============  ============  ==================  ==============
Disk Lifetime  Cost Per Disk  Disks per TB  Yearly Cost per TB  Cost per year [#a]_
=============  =============  ============  ==================  ==============
3              $300           3             $300                $1500
=============  =============  ============  ==================  ==============


Networking
^^^^^^^^^^

It is critical for the security of the server that they be on an
isolated network segment which is provided by hardware with up-to-date
firmware. Since network traffic will be directed inward to the data
center from the external WAN connection, out-of-date unsupported
firmware is a critical security vulnerability.

An example would be a Dell Sonicwall Next Generation Firewalls (NGFW)
gateway appliance, like a TZ300. These networking appliances have an
initial purchase cost and an ongoing licensing cost for keeping firmware
up to date and in-spec. Example costs are described below

===============   =====================   ===================
Appliance         Initial Purchase Cost   Yearly License Cost
===============   =====================   ===================
SonicWall TZ300   $625                    $400
===============   =====================   ===================


Monitoring
^^^^^^^^^^

The IT administrator managing the system will require the ability to
monitor the systems. For example, if hard drives are configured in a
RAID-10 configuration and a drive fails it is critical for an
administrator to be notified immediately to ensure the drive is replaced
rapidly and the system is not at risk of data loss.

A standard on-premise tool for managing servers is Nagios, with cost
details provided below

=========   =====================   ===================
Appliance   Initial Purchase Cost   Yearly License Cost
=========   =====================   ===================
Nagios      $1,995                  $1,695
=========   =====================   ===================


Backups / Disaster Recovery
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to the primary production environment, there needs to be a
location for backups to be stored, which will require a second redundant
system which may or may not already be available at the existing
datacenter.

Prices for storing backups can vary dramatically based on the backup
architecture, but the most basic back-of-envelope costs would be to
double the cost of storage (possibly with slower disks), if an existing
system is available to host backups. Alternatively a second, lower power
host server can be procured as well.


Support Licenses
^^^^^^^^^^^^^^^^

Cloud hosting data centers which are managing servers at the OS level
will generally have `licensed support for Operating Systems <https://ubuntu.com/legal/ubuntu-advantage-service-description>`_.
This support ensures that IT Admins are able to provide seamless uptime
for servers and resolve critical issues at the OS level if they occur.


Representative Yearly Costs
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Taking into account the above, a reasonable estimate for a baseline
yearly cost over a 5 year period would include the following

========   =======   ==========   ==========   ======   =======
Hardware   Storage   Networking   Monitoring   Yearly   Monthly
========   =======   ==========   ==========   ======   =======
$1,600     $1,500    $400         $1,695       $5,195   $433
========   =======   ==========   ==========   ======   =======

Some of these costs may be shared between different server systems,
reducing the monthly cost, which is how Cloud providers are able to make
these systems available more cheaply.

Due to the more complex pricing these costs do not include

* "One-time" costs for extra disks or initial purchases of Nagios/network
  appliances
* Backups
* Costs of maintenance
* Subject Matter Expert (SME) support for OS’s or services
* Costs to replicate Information Security Management (ISMS) protocols
  including Physical Access control and regular auditing

All of which are important considerations for individual programs


.. [#a] The recommendation for a monolith is 1TB of storage per year of
   project. On flexible block storage, this cost could be calculated
   with storage as needed (i.e. 1TB year 1, 2TB year 2, 3TB year 3,
   etc.), but with self-hosted RAID storage extending the storage volume
   requires new disks, which is complex. A minimum cost would be 3TB for
   years 1, 2, and 3, then 5TB years 4 and 5, which would require a
   complex migration requiring subject matter expertise.
