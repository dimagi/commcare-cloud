# 2. Use syslog-ng as the logging framework of choice

Date: 2019-08-15

## Status

Proposed

## Context

One component of monitoring CommCare is log collection and analysis. At the time of writing
there is no centralized log collection or storage system in place. Individual process logs are
stored on the machines where the process is running.

There are a few logs that are converted into DataDog metrics and sent to DataDog:

* nginx timing / request logs
* nginx error logs
* couchdb timing

For these logs we do not send the raw log but rather convert the log lines into specific metrics
to track request times, errors and apdex.

This log processing is currently handled by the DataDog v5 in the form of
[Python functions](https://github.com/dimagi/datadog-parsers) which are
executed by the agent on the logs. Version 6 of the agent does not support this functionality and
although v5 of the agent is still supported it requires Python 2.7 which has reached end of life and so
will be deprecated soon.

In order to facilitate the upgrade of the agent it is necessary to move the log processing
functionality to a different system. The system that gets chosen should have the following characteristics:

* low CPU and memory consumption
* able to process the necessary volume of logs
* able to support the logic currently encoded in the Python parsing functions
* support future log shipping requirements where possible
* ideally be an 'off the shelf' tool rather than a tool developed by Dimagi

## Decision

After consideration syslog-ng came out as the top choice for the following reasons:

* lightweight
* good documentation (relative to others)
* easy configuration
* able to support what we need or be easily extended
  * able to encode the enrichment that we apply, particularly for URL grouping
  * able to send the data either to statsd via TCP / UDP
    or to Datadog directly via HTTP API

The options considered are listed below.

#### [rsyslog](https://www.rsyslog.com/)

Pros:
* Default logging application installed with Ubuntu
* High performance
* Light weight

Cons:
* Difficult to configure
* Difficult to extend

#### [LogStash](https://www.elastic.co/products/logstash)

Pros:
* Powerful processing and output capabilities

Cons:
* Heavy on memory and CPU
* Requires Java

#### [FluentBit](http://fluentbit.org/)

Pros:
* Lightweight
* Extendable parsing and processing via Lua scripts
* Easy to configure

Cons:
* Custom network / HTTP output required to send data to Datadog / StatsD not supported

The recommended setup for FluentBit is to use it to collect and pre-process logs before
shipping them to FluentD for final processing and output. This is a similar architecture to
FileBeat and Logstash.

#### [syslog-ng](https://www.syslog-ng.com/)

Pros:
* Lightweight and high performance
* Simpler configuration than rsyslog
* Easy extension using python

Cons:
* Requires replacing default system logging tool


## Consequences

Installation of syslog-ng will deactivate rsyslog and replace it's functionality. This will require
a few changes to commcare-cloud where we configure rsyslog e.g. for HA Proxy.
