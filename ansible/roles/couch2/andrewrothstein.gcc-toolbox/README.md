[![CircleCI](https://circleci.com/gh/andrewrothstein/ansible-gcc-toolbox.svg?style=svg)](https://circleci.com/gh/andrewrothstein/ansible-gcc-toolbox)
andrewrothstein.gcc-toolbox
=========

[GCC](https://gcc.gnu.org/) tools

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
    - andrewrothstein.gcc-toolbox
```

License
-------

MIT

Author Information
------------------

Andrew Rothstein <andrew.rothstein@gmail.com>
