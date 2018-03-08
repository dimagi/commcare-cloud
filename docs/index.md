# Overview

Dimagi is proud to be able to share **CommCare Cloud**,
our toolkit for deploying and maintaining CommCare servers,
with our fabulous developer community.

We wrote CommCare Cloud for ourselves,
and it's what we use to manage [CommCare HQ](https://www.commcarehq.org/),
our subscription offering.
Anyone willing to dedicate the considerable amount of effort
and system administration knowledge necessary to stand up and manage a CommCare server
cluster will be able to do so using the same tools that we do.

## A word of caution

CommCare HQ is a complex, distributed software application,
made up of dozens of processes
and several pieces of third-party open source database software.
It has been built for scale rather than simplicity,
and as a result even for small deployments a CommCare server or server cluster
can be challenging to maintain.
An organization endeavoring to manage their own CommCare server environment
must be willing to devote **considerable effort and system administration capacity**
not only in the initial phases of provisioning, setup, and installation,
but in steady state as well.

If you or your organization is hosting or interested in hosting
its own CommCare server environment,
we strongly suggested you read our [Hosting Considerations](hosting-considerations) page
before going any further.

## CommCare HQ in Production: System Overview

Before proceeding, we highly recommend that you gain a high-level understanding
of what a CommCare HQ production system looks like
by consulting our [System Overview](system-overview) page.
CommCare Cloud will help you stand up a system like the one described on that page,
but maintaining it---even with the help of CommCare Cloud's helpful tooling---will require
an understanding of the system's architecture and each of the system's underlying technologies.

## Miscellaneous Links
- The [commcare-cloud Repo README](https://github.com/dimagi/commcare-cloud/blob/master/README.md)
- The [ansible README](https://github.com/dimagi/commcare-cloud/blob/master/ansible/README.md) (somewhat outdated)

## HowTos
- [Moving partitioned databases](howto/move-partitioned-database)
