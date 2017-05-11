[![CircleCI](https://circleci.com/gh/andrewrothstein/ansible-couchdb.svg?style=svg)](https://circleci.com/gh/andrewrothstein/ansible-couchdb)
andrewrothstein.couchdb
===========================

Installs [Apache CouchDB](http://couchdb.apache.org/).

Requirements
------------

See [meta/main.yml](meta/main.yml)

Role Variables
--------------

See [defaults/main.yml](defaults/main.yml)

Dependencies
------------

See [meta/main.yml](meta/main.yml)

Example Playbook
----------------

```yml
- hosts: servers
  roles:
    - andrewrothstein.couchdb
```

License
-------

MIT

Author Information
------------------

Andrew Rothstein <andrew.rothstein@gmail.com>
