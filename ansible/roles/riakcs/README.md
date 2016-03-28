# System Overview

For a system overview look [here](https://docs.google.com/document/d/1F5KjtyXmvGcl4nHf6U8_teMgM4ezo0OJPCUN0AOiGo8/edit#heading=h.9iy7nsyi5rzy)

## Configuring RiakCS (if not running full `deploy_stack`)

1. Populate `[riakcs]` and `[stanchion]` host groups in the inventory file

2. Run `deploy_proxy` to update Nginx with the new configs to allow webworkers to communicate with RiakCS cluster

3. Optional: run `deploy_stack --tags=datadog --limit=riakcs` to setup the datadog monitoring agent.

4. Run `deploy_riakcs` to deploy the Riak CS cluster

## Role layout

The `riakcs` role is structured slightly differently than most simpler roles. It contains four reusable sub-roles:

- riakcs
  - install
  - configure
  - create_admin_user
  - sync_keys

After configuring `[riakcs]` and `[stanchion]` inventory host groups, the `deploy_riakcs.yml` playbook will setup a fully functional Riak CS cluster. It is idempotent and can be used to add more nodes to an existing Riak CS cluster (removing nodes must be done manually). All tasks will be skipped if the `[riakcs]` and `[stanchion]` host groups are empty or missing.

A new set of admin user keys will be created if a new node is added as the first host in the `[riakcs]` host group. Any existing admin user keys will continue to be valid, but will no longer be used in cluster config files. Adding a host anywhere else in the group will configure it with the user keys of the first host.

## Troubleshooting

Riak has particularly painful error messages to debug, here are a few tips and tricks along the way

- A lot of useful log information gets sent to `/var/log/<riak|riakcs|stanchion>/console.log
- Always use IP addresses and not hostnames in conf
- Start machines in this order:
  1. Riak
  2. RiakCS
  3. Stanchion

Reference material:

- http://download.freenas.org/10/MASTER/RiakHowto.pdf
- http://littleriakbook.com/
