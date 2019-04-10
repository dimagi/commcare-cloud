Dimagi is proud to be able to share **CommCare Cloud**,
our toolkit for deploying and maintaining CommCare servers,
with our fabulous developer community.

We wrote CommCare Cloud for ourselves,
and it's what we use to manage [CommCare HQ](https://www.commcarehq.org/),
our subscription offering.
Anyone willing to dedicate the considerable amount of effort
and system administration knowledge necessary to stand up and manage a CommCare server
cluster will be able to do so using the same tools that we do.

## What is commcare-cloud?

`commcare-cloud` is a python-based command line tool that uses
the open source technologies Ansible and Fabric to automate everything
you need in order to run a production CommCare cluster.

While it is possible to install on a laptop with a linux-like command line interface,
it is primarily designed to be run on the machine that is hosting CommCare.
(If you are hosting CommCare on more than one machine,
`commcare-cloud` only needs to be installed on one of them.)
In this documentation, we will call the machine on which `commcare-cloud` is installed
the "control machine". If you are hosting CommCare on a single machine,
that machine is also the control machine.

## System installation

- [Installation](setup/installation.md)
- [Troubleshooting first time setup](setup/troubleshooting.md)
- [Changelog](changelog)

## Usage

- [Command Usage](commcare-cloud/commands)
- [Telling `commcare-cloud` about your environments](commcare-cloud/env)
- [Server Management Basics](commcare-cloud/basics)

## Services
- CouchDB
    - [Add a new CouchDB node to an existing cluster](howto/add-couchdb2-node.md)
- [PostgreSQL](services/postgresql.md)
- Proxy
    - [Enable HTTPS](howto/enable-https.md)
- RiakCS/S3
    - [Migrate from one S3 backend to another](howto/migrate-s3-to-s3.md)
- Firewall
    - [Configure a firewall on the servers](howto/firewall.md)
- [Kafka](services/kafka.md)

## Optional but recommended
- [Set up Sentry for error messages](howto/set-up-sentry.md)
- [Firefighting](firefighting/index.md)

## Specialized howtos
- [White label a CommCare instance](howto/white-label.md)

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
we strongly suggest you read our [Hosting Considerations](system/hosting-considerations.md) page
before going any further.

## CommCare HQ in Production: System Overview

Before proceeding, we highly recommend that you gain a high-level understanding
of what a CommCare HQ production system looks like
by consulting our [System Overview](system/system-overview.md) page.
CommCare Cloud will help you stand up a system like the one described on that page,
but maintaining it---even with the help of CommCare Cloud's helpful tooling---will require
an understanding of the system's architecture and each of the system's underlying technologies.
