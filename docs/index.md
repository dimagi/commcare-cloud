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

## System installation basics

- [Getting started guide](basics)
- For manual install instructions see the [README](https://github.com/dimagi/commcare-cloud/blob/master/README.md)
- [Troubleshooting first time setup](basics/troubleshooting.md).
- [Changelog](changelog)

## HowTos
- CouchDB
    - [Add a new CouchDB node to an existing cluster](howto/add-couchdb2-node)
- PostgreSQL
    - [Backup PostgreSQL](howto/add-barman-server.md)
    - [Moving partitioned databases](howto/move-partitioned-database)
- Proxy
    - [Enable HTTPS](howto/enable-https.md)
- RiakCS/S3
    - [Migrate from one S3 backend to another](howto/migrate-s3-to-s3.md)


## Reference material

- [Command Usage](commcare-cloud/commands)
- [Telling `commcare-cloud` about your environments](commcare-cloud/env)
- [Server Management Basics](commcare-cloud/basics)

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
