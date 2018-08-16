# Hosting Considerations

If you are interested in running a CommCare server environment there are a number of serious
obstacles to consider before taking the plunge. If you are already managing a CommCare
server environment and are finding it challenging,
you may also find thinking about the considerations listed here helpful
before deciding your next steps.

## Physical Server Management

This section is for people interested in owning the physical hardware running their servers.
If you will be using an established data center or modern hosting provider,
you can skip down to CommCare Cluster Management.

It can be tempting to want to run CommCare HQ on server hardware that you own. After all,
a server is just a computer connected to the internet, with enough RAM, CPU, and Disk
to run the software it's hosting. However, in practice, there's a lot more that goes into it.

### Network Connection

One of the biggest difficulties in maintaining physical server hardware is that to be reliable
it must **always** be connected to the internet over a stable and reliable network.
In many of the areas of the world that are most interested in self-hosting
for data-sovereignty reasons, network connectivity is notoriously spotty.
Real data centers will go to great lengths to keep their servers always connected
to the public internet, including network redundancy.
It can be close to impossible to do this at the level of one or two servers in an office,
so in practice, these servers will experience large rates of downtime.

### Power Source

Another often-overlooked challenge with managing physical hardware is maintaining a reliable
power source. In many areas of the world that use CommCare, reliable power is not a given.
Even with a generator, unless there's a sophisticated battery backup system in place,
it will take a number of seconds for the generator to kick in, and even the slightest blip
in power supply will cause a server to shut off without warning.
Thus, without a well-planned system in place for maintaining consistent power even through a
grid outage, these servers will experience a lot of downtime and will be at risk for
data corruption as a result of powering off without warning.

### Physical Security

Real data centers are highly guarded by security personnel and have authorization protocols
preventing physical access to the servers except by a small handful of entrusted individuals.
With physical access to a machine,
a malicious or unwitting person can steal private information
or cause untold damage including deletion of all data.
In the typical office environment, maintaining an appropriate level of physical security
around the hardware is not a given, and will require concerted effort and planning.

### Temperature Control

Computer hardware gives off a tremendous amount of heat. Servers are **hot**,
and so are many of the areas of the world that use CommCare.
Real data centers are carefully designed to manage heat flow and sites are often specifically
chosen for environmental features such as cold outdoor temperature or proximity to a vast
water source for cooling. Overheating is a very real issue and when it happens
it will lead to unpredictable hardware failure.


## CommCare Cluster Management

CommCare HQ is a complex, distributed software application,
made up of dozens of processes
and several pieces of third-party open source database software.
It has been built for scale rather than simplicity,
and as a result even for small deployments a CommCare server or server cluster
can be challenging to maintain.

### Many processes

While the setup automation should work out of the box, once you're up and running
you will have to troubleshoot any issues yourself. This means being familiar enough with
every piece of third-party database software to be able to debug issues
and bring it back to life or recover from some other bad state;
it also means understanding what each of the many types of CommCare application processes does
well enough to troubleshoot issues.

CommCare HQ relies on the following open source technologies:

- PostgreSQL
  - PL/Proxy and a custom sharding setup
  - `pg_backup` and streaming replication
- CouchDB
- Redis
- Riak/Riak CS (mandatory for multi-server environments)
- Elasticsearch
- Kafka (and Zookeeper)
- RabbitMQ
- Nginx

CommCare HQ also employs different types of application processes
each with its own distinct purpose and set of functionality:

- Web workers
- Asynchronous task processors (Celery)
- [ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load) processes ("Pillowtop")
  that themselves come in a number of different flavors and fill a number of different roles
- The CommCare mobile engine exposed as a webservice ("Formplayer")

You will also need some familiarity with the following sysadmin tools:
- Monit
- Supervisor
- Ansible
- Fabric
- EcryptFS
- [LVM](https://en.wikipedia.org/wiki/Logical_Volume_Manager_%28Linux%29) (optional)

---

[︎⬅︎ Overview](..)
