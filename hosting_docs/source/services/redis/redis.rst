
Redis
=====

Usage in CommCare
-----------------

`Redis <https://redis.io/>`_ is an open source, in-memory data structure store. CommCare uses Redis
for caching and locking.

Guides
------


* `Setting up a Redis cluster <redis/redis_cluster.md>`_

Tools
-----


* `Redis Traffic Stats <https://github.com/hirose31/redis-traffic-stats>`_

Configuration recommendations
-----------------------------

Disk
^^^^

You should allocate at least 3x as much disk for redis data as the redis ``maxmemory`` setting.

If you define a ``redis_maxmemory`` variable in your environment's public.yml then that will be the value. Otherwise it will be half of the total memory of the machine.

So for example if ``redis_maxmemory`` is not set and you're running redis on an 8GB machine, then redis's ``maxmemory`` setting will be 4GB and you should allocate at least 4GB x 3 = 12GB of disk for redis data (in addition to whatever other disk space needed for the OS, logs, etc.). This will allow enough room for redis's AOF (data persistence file), whose rewrite process makes it oscillate between at most ``maxmemory`` and at most ``3 x maxmemory`` in a saw-tooth fashion.
