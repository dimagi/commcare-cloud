# Logstash

Master: [![Build Status](https://travis-ci.org/sansible/logstash.svg?branch=master)](https://travis-ci.org/sansible/logstash)  
Develop: [![Build Status](https://travis-ci.org/sansible/logstash.svg?branch=develop)](https://travis-ci.org/sansible/logstash)

* [Installation and Dependencies](#installation-and-dependencies)
* [Tags](#tags)
* [Examples](#examples)

This roles installs Logstash for the ELK stack.

For more information on Logstash please visit
[elastic logstash](https://www.elastic.co/products/logstash).


## Installation and Dependencies

This role will install `sansible.users_and_groups` for managing `logstash`
user and `sansible.java` for installing java.

To install run `ansible-galaxy install sansible.logstash` or add this to your
`roles.yml`

```YAML
- name: sansible.logstash
  version: v2.1.x
```

and run `ansible-galaxy install -p ./roles -r roles.yml`


## Tags

This role uses two tags: **build** and **configure**

* `build` - Installs Logstash and all it's dependencies.
* `configure` - Configure and ensures that the Logstash service is running.


## Examples

To install:

```YAML
- name: Elk Logstash
  hosts: "{{ hosts }}"

  roles:
    - role: sansible.logstash
```

To install 5.* version:

```YAML
- name: Elk Logstash
  hosts: "{{ hosts }}"

  roles:
    - role: sansible.logstash
      sansible_logstash_family: 5.x
      sansible_logstash_version: 1:5.4.*
```

To install 6.* version:

```YAML
- name: Elk Logstash
  hosts: "{{ hosts }}"

  roles:
    - role: sansible.logstash
      sansible_logstash_family: 6.x
      sansible_logstash_version: 1:6.6.*
```


With your own config files:


```YAML
- name: Elk Logstash
  hosts: "{{ hosts }}"

  roles:
    - role: sansible.logstash
      sansible_logstash_default_config: no

  tasks:
    - name: Configure logstash
      become: yes
      template:
        src: "{{ item }}.j2"
        dest: "/etc/logstash/conf.d/{{ item }}"
      with_items:
        - templates/01-inputs.conf
        - templates/10-filters.conf
        - templates/90-outputs.conf
      notify:
        - restart logstash
```
