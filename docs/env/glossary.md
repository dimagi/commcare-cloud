## Host string

A "host string" is either
- the IP address or FQDN of a host exactly as specified in `inventory.ini`.
  In an Ansible context, this is the same as the value of `inventory_hostname`.

or

- the name of a group heading in `inventory.ini` that contains a single host.


### Host string example

Given the following inventory file:
```
# example/inventory.ini
...
[pg0]
10.0.0.01

[pg1]
10.0.0.02

[postgresql:children]
pg0
pg1
...
```

`"pg0"` and `"10.0.0.01"` are valid host strings referring to the same machine;
`"postgresql"` is _not_ a valid host string, because it contains more than one machine.
