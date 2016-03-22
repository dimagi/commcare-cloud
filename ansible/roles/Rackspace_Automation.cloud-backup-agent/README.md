cloud-backup-agent
========

[![Build Status](https://drone-opsdev.rax.io/github.com/rack-roles/cloud-backup-agent/status.svg?branch=master)](https://drone-opsdev.rax.io/github.com/rack-roles/cloud-backup-agent)

This role installs and configures the Rackspace Cloud backup agent.

Requirements
------------

None.

Role Variables
--------------

* `rackspace_username`: Pass your Rackspace username to configure the agent.
* `rackspace_apikey`: Pass your Rackspace apikey to configure the agent.

Dependencies
------------

None

Example Playbook
-------------------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: Rackspace_Automation.cloud-backup-agent, x: 42 }

License
-------

BSD

Author Information
------------------

[Rackspace - the open cloud company](http://rackspace.com)

Ask about our DevOps Automation Service - [www.rackspace.com/devops](http://rackspace.com/devops)
