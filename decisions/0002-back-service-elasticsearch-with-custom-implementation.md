# 2. Back service elasticsearch with custom implementation

Date: 2018-05-11

## Status

Accepted

## Context

The `service` command is has become a useful way for us to start, stop, restart,
and check the status of the many service processes behind a commcare cluster.
For the most part, these commands map very predictably to a start/stop/restart/status
command on either [`service`](https://linux.die.net/man/8/service) or `supervisorctl`.

Recently and in the past, we have found that `elasticsearch` does not stop or restart
reliably. In particular, after running `service elasticsearch stop`,
using `ps aux | grep elasticsearc[h]` may still show a running Elasticsearch
process, even if `service` is reporting a stopped status. This then requires
killing the rogue process in order for a `start` to bring up a genuinely new process.

Before the addition of the `service` command, we already had the `restart-elasticsearch`
command, which is conceptually (though currently not functionally) equivalent to
`... service elasticsearch restart`. It does not address the above issue of rogue
processes, but it does address some other issues, including a reminder to stop all pillows,
as well as theoretically providing rolling (and thus no-downtime) restart,
which we currently do not benefit from because we do not store data in duplicate.

## Decision

We will be changing `... service elasticsearch ...` from using the default
behavior to performing a more targeted set of actions that are guaranteed to achieve the
stop/start/restart/status action, and we will also be deprecating the `restart-elasticsearch`
entry point. In particular, `... service elasticsearch stop` will

- stop pillows
- guarantee the process has stopped and `kill -9` it after a period of time if it has not

and `start` will

- start pillows

and `restart` will be functionally a `stop` followed by a `start`.

Pros:
- Someone with little context will be able to run a `... service elasticsearch ...`
  and have it have the intended overall consequence
- The tool will incorporate what is currently heard knowledge

Cons:
- A "power" user may think of the command as executing a very specific other command,
  and may be taken aback by the tool trying to outsmart them.

To mitigate this con, the command will also explain itself beforehand,
and print out the command you could run to execute the narrower command,
and ask for confirmation before continuing.
See https://github.com/dimagi/commcare-cloud/pull/1721#discussion_r187730933
for a short exchange that demonstrates this trade-off.

## Consequences

Going forward, we will expect `service` commands to achieve the desired action
by whatever means the team has deemed effective, rather than by executing a predictable
set of commands that are the same across services.

It also means that there will be more code to maintain surrounding these more custom
service actions.
