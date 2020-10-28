# Redis

## Usage in CommCare

[Redis](https://redis.io/) is an open source, in-memory data structure store. CommCare uses Redis
for caching and locking.

## Guides
- [Setting up a Redis cluster](redis/redis_cluster.md)

## Tools
* [Redis Traffic Stats](https://github.com/hirose31/redis-traffic-stats)

## Configuration recommendations

### Disk

You should allocate at least 3x as much disk for redis data as the redis `maxmemory` setting.

If you define a `redis_maxmemory` variable in your environment's public.yml then that will be the value. Otherwise it will be half of the total memory of the machine.

So for example if `redis_maxmemory` is not set and you're running redis on an 8G machine, then redis's `maxmemory` setting will be 4G and you should allocate at least 4G x 3 = 12G of disk for redis data (in addition to whatever other disk space needed for the OS, logs, etc.). This will allow enough room for redis's AOF (data persistence file), whose rewrite process makes it oscillate between at most `maxmemory` and at most `3 x maxmemory` in a saw-tooth fashion.
