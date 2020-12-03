## Overview

Docker setup for couchdb to try to reproduce the inconsistent document counts.
As of now, unable to reproduce.

## Installation

`pip install -r requirements.txt`

### Cluster Up
We first need to create the cluster. The easieast way I do this is via the python shell.

```
$ python
>>> import steps as steps
>>> steps.cluster_up()
```
If you see `curl: (52) Empty reply from server`, the couchdb server took
too long to start up for the curl commands to register, so wait a few seconds
and run `steps.cluster_up()` again.

Then go to `http://localhost:5984/_membership` and make sure that `all_nodes` has 3 entries.
Example:
```
{"all_nodes":["couchdb@couchdb-0.docker.com","couchdb@couchdb-1.docker.com","couchdb@couchdb-2.docker.com"],"cluster_nodes":["couchdb@couchdb-0.docker.com","couchdb@couchdb-1.docker.com","couchdb@couchdb-2.docker.com"]}
```

## Running

```
python steps.py
```

The final step checks to see if the nodes are inconsistent. We have a timeout to wait
for the replication to finish, and so sometimes this is not enough and the script
reports inconsistency too early. I would run `db_is_inconsistent()` in a shell
to verify just in case.

I was not able to reproduce it, but maybe if we toggle a few events and timings 
we can.


## Cluster down

If you need to recreate the cluster, run `cluster.cluster_down()` similar to 
cluster up.


