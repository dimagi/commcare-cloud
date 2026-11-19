# Logstash

Installs Logstash 5.x or later from Elastic's apt repo, with the CommCare
pipeline config, for `deploy_logstash.yml`.

Based on [sansible/logstash](https://github.com/sansible/logstash) v2.4.4,
merged with the logstash role from
[dimagi/commcare-logstash](https://github.com/dimagi/commcare-logstash)
0.9.5.

It depends on `sansible.java`, which installs Java, and creates the
`logstash` user and group itself.


## Tags

This role uses two tags: **build** and **configure**

* `build` - Installs Logstash and its dependencies.
* `configure` - Configures Logstash and ensures that its service is running.


## Variables

See `defaults/main.yml`. `logstash_version` must belong to
`logstash_family`, which selects the Elastic apt repo.


## Example

As `deploy_logstash.yml` uses it:

```YAML
- name: Logstash
  hosts: logproxy
  become: yes
  tasks:
    - import_role:
        name: logstash
```
