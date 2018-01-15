These files represent the initial version of a proposed spec for automating a datacenter migration. Note that there are no tools built around this yet.

Imagine something like

```
commcare-cloud icds migration 2017-12-01-initial run postgresql
```

which would look at the mapping you'd specified of postgresql machines and initiate pairwise rsyncs. And then maybe

```
commcare-cloud icds migration 2017-12-01-initial check postgresql
```

would show you some progress information about the ongoing migration, as well as useful information like what logfiles to check to see the raw output of rsync commands, etc. for debugging. Anyway, that's the dream.

## The format

- the big file `couchdb2-cluster-plan.yml` is just the plan file from `couchdb-cluster-admin` converted to YAML. This outlines the sharding plan that `couchdb-cluster-admin` will eventually commit, and thus also which data needs to be copied to which machine.
- the `role-mapping.yml` file is really the payload here. It outlines for each data service which machine-to-machine data transfers need to happen. You can read it as saying "for the purposes of `postgresql`, `icds` `pg1` corresponds to `icds-new` `pgmain`", "for the purposes of `riackcs`, `icds` `pg1` corresponds to `icds-new` `riak0`", etc.

## The rationale
Thinking back to the data-migration part of the migration, I'm pretty sure that this right here captures most if not all of what a computer would need to know about the particulars of that migration in order to run it automatically, or at least run parts of it automatically though commands like the ones above.

The other nice thing is that even before we add any super-sophisticated automation, having this down in a spec can:
- let people manually verify that they're migrating to and from the right IPs—it's right here in the spec what's supposed to go where
- let people write scripts that generate the rsync commands that they should manually run (instead of manually copying and pasting IP addresses to form the commands themselves)
- leave a simple formal record of what was supposed to happen in each migration.
- serve as a focal point for building simple tools around that will eventually snowball into something super useful
