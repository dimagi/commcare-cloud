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
