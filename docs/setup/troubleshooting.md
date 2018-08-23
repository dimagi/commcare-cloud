# Troubleshooting first time setup

## My site is showing "Internal Server Error"

If you are seeing a blank screen with just the words "Internal Server Error" on it,
it means that the django webworker process is not reporting as "down",
but still failing to bootstrap fully.
(If you are seeing a more elaborate 500 page, then that is an issue with a single request,
but ususally does not indicate a more pervasive problem with the site's ability to receive and handle requests in general.)
Often this is because it is unable to connect to
a backing service (such as CouchDB, Redis, PostgreSQL, PgBouncer, Elasticsearch, Riak).
This in turn can fall into a number of categories of issue:
1. the service is down
2. the service is up, but unreachable due to network configuration
3. the service is up and reachable, but is blocking the connection for a permissions-related reason
   (auth is wrong, IP is not whitelisted, etc.)
4. the service is up, reachable, and accepting the connection,
   but is failing due to other problems such as misconfiguration (e.g. a low max connection limit),
   or other problem such as out of memory errors.

### Further diagnosis
You can start by simply checking which of the backing services
the application code is able to connect to by running

```bash
commcare-cloud <env> django-manage check_services
```

Note that this checks the availability of each service _to the application code_,
so it could be any type of problem given in 1-4 above.

### Steps to fix

If a stack trace you find in the logs points at a service being down, you can check its status
and start it if it's stopped or restart it if it's "up" but causing problems. In the command below
replace the word "postgresql" with the name of the service at issue:

```bash
commcare-cloud <env> service postgresql status
commcare-cloud <env> service postgresql start  # to start it or
commcare-cloud <env> service postgresql restart  # to restart it
```

### Digging into the problem

If that doesn't fix it, you will need to dig a bit deeper.

Start by checking which of the application services are reporting as up
by running

```bash
commcare-cloud <env> service commcare status
```

You will likely find the `django` process is reporting as RUNNING.
Some other processes if affected by a similar issue may (or may not) be reporting as FATAL "exited too quickly".

To dig into a particular error, you can log into the machine and tail one of the logs:

```bash
commcare-cloud <env> ssh webworkers:0
$ tail -n100 /home/cchq/www/<env>/log/django.log
```

or, if you do not want to figure out where a particular log lives, you can run the command on all machines
(allowing that it'll fail on any machine that doesn't contain that particular log):

```bash
commcare-cloud <env> run-shell-command all 'tail -n100 /home/cchq/www/<env>/log/django.log'
```

or, you can use the output from the status command above and run it through the `supervisorctl` command:

```bash
commcare-cloud <env> ssh <machine>
$ sudo supervisorctl tail -f <supervisor process name>
```

## One of the setup commands is showing...
### `RequestError: socket.error: [Errno 111] Connection refused`

This means that CouchDB is unreachable.


#### Breakdown of a request to CouchDB

Note: if you are running on a recommended single-machine setup,
then you can ignore the host groups (denoted `[in brackets]`):
all services will be running on the same machine.


Requests to CouchDB are made over HTTP,
and are normally routed the following way:
1. They start at the originator of the request,
   such as a Django web worker
2. They are made to port 25984 on host `[couchdb_proxy]`,
   which is served by the `nginx` web server, acting as a load balancer.
3. `nginx` passes them through to one of the `couchdb2` nodes
   (or _the_ `couchdb2` node if you have only one),
   which handles the requests.

```
[webworkers] [couchdb2_proxy] [couchdb2]
django  -->  nginx  -------->  couchdb2
             port 25984        port 15984
```

The following table represents the general case
and includes variables that may be overriding the default port values:

|   |  host group  |  service  |  port (default value) |  port (variable name) |
|---|--------------|-----------|-----------------------|-----------------------|
| Originator | various | various |  |  |
|  | ⇩ |  |  |
| CouchDB Load Balancer | `[couchdb2_proxy]` | `nginx` | 25984 | `couchdb2_proxy_port` |
|  | ⇩ |  |  |
| CouchDB Node | `[couchdb2]` | `couchdb2` | 15984 | `couchdb2_port` |


#### How to confirm the issue

To confirm the issue, that django processes cannot reach CouchDB, run

```bash
commcare-cloud <env> django-manage check_services couch
```

It should tell you that CouchDB is unreachable.

#### How to solve

The first thing to check is whether couchdb2 and couchdb2_proxy
services are up, which you can do with the single command:

```bash
commcare-cloud <env> service couchdb2 status
```

If one of the services is reporting down, you can use the following
to start it:

```bash
# Start both
commcare-cloud <env> service couchdb2 start

# or start only couchdb2
commcare-cloud <env> service couchdb2 start --only couchdb2

# or start only couchdb2_proxy
commcare-cloud <env> service couchdb2 start couchdb2_proxy
```

If CouchDB is still unreachable, try hitting each of the individual
parts.

1. Test whether `couchdb2` is responding
    ```bash
    commcare-cloud <env> ssh couchdb2
    curl <couchdb2-internal-IP-address>:15984
    ```
2. Test whether the load balancer on `couchdb2_proxy` is responding
    ```bash
    commcare-cloud <env> ssh couchdb2_proxy
    curl <couchdb2_proxy-internal-IP-address>:25984
    ```

Notes:
- You will often see the value for `<couchdb2-internal-IP-address>`
printed out next to `eth0` upon `ssh`ing into the machine.
- For a single-machine setup, no need to separately ssh for each step.


##### Is the CouchDB `nginx` site on `couchdb2_proxy` enabled? 

```bash
commcare-cloud <env> ssh ansible@couchdb2_proxy
ls /etc/nginx/sites-enabled
```
This should contain a file with "couchdb" in the name.


##### Are there errors in the `couchdb2` logs?
```bash
commcare-cloud <env> ssh ansible@couchdb2
ls /usr/local/couchdb2/couchdb/var/log/
```
There should be some logs in there that you can tail
or grep through for errors.

---

[︎⬅︎ Overview](..)
