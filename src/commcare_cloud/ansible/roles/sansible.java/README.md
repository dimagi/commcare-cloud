# java

Master: [![Build Status](https://travis-ci.org/sansible/java.svg?branch=master)](https://travis-ci.org/sansible/java)
Develop: [![Build Status](https://travis-ci.org/sansible/java.svg?branch=develop)](https://travis-ci.org/sansible/java)

* [ansible.cfg](#ansible-cfg)
* [Installation and Dependencies](#installation-and-dependencies)
* [Tags](#tags)
* [Examples](#examples)

This roles installs OpenJDK Java, any version can be installed
but 7 is used by default (which may not be available on all O/S releases).

*NOTE:* Only x86_64 is supported.


## Installation and Dependencies

This role has no dependencies and has been tested with Ansible 2.2+.

To install run `ansible-galaxy install sansible.java` or add this to your
`roles.yml`

```YAML
- name: sansible.java
  version: v2.1
```

and run `ansible-galaxy install -p ./roles -r roles.yml`


## Tags

This role uses one tag: **build**

* `build` - Installs OpenJDK Java.


## Arguments

Argument | Default | Description
----------|---------|------------

sansible_java_apt_key_id | EB9B1D8886F44E2A | Fingerprint of PGP used to verify repo
sansible_java_apt_keyserver | http://eu.pool.sks-keyservers.net | Keyserver to grab PGP key from
sansible_java_apt_repo | See defaults | The repo to grab packages from
sansible_java_set_as_default | yes | Set the installed version as default
sansible_java_version | 8 | The Java version to be installed


## Example Playbook

To install OpenJDK Java 7:

```YAML
- name: Install Java
  hosts: sandbox

  roles:
    - name: java
```

To install OpenJDK Java 8:

```YAML
- name: Install Java
  hosts: sandbox

  roles:
    - name: java
      java:
        version: 8
```
