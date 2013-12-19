redis
=====

This role helps to deploy a Redis master or replication server on target host.
This roles sets several default values for Redis configuration which can be
overrriden by the user.

Requirements
------------

This role requires Ansible 1.4 or higher, and platform requirements are listed
in the metadata file.

Role Variables
--------------

The variables that can be passed to this role and a brief description about
them are as follows. See the documentation for Redis for details:

	redis_port: 6379            # Port for redis server
	syslog_enabled: "yes"       # enable_syslog
	databases: 16               # Set number of databases
	database_save_times:        # Save the DB on disk (seconds changes)
	  - [900, 1]
	  - [300, 10]
	  - [60, 10000]
	dbfilename: dump.rdb        # Filename for the db
	db_dir: /var/lib/redis      # DB directory
	redis_role: master          # The role for this redis deployment (master/slave)
	requirepass: false          # If password is required for querying
	redis_pass: None            # Password if require_pass is enabled
	max_clients: 128
	max_memory: 512mb
	maxmemory_policy: volatile-lru
	appendfsync: everysec       # How often to sync the filesystem

	# If redis_role is "slave", set these values too
	master_ip: 1.1.1.1          # The master's IP
	master_port: 6379           # master port
	master_auth: None           # master auth

Examples
--------

The following example sets up a master Redis server.

	- hosts: all
	  sudo: true
	  roles:
	  - {role: redis, redis_port: 11244}

The following example sets up a slave Redis server.

	- hosts: all
	  sudo: true
	  roles:
	  - {role: redis,
	     redis_role: 'slave',
	     master_ip: '192.168.2.10',
	     master_auth: 'foobar'}


Dependencies
------------

None

License
-------

BSD

Author Information
------------------

Benno Joy


