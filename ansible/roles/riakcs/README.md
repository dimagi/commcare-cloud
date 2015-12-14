# System Overview

For a system overview look [here](https://docs.google.com/document/d/1F5KjtyXmvGcl4nHf6U8_teMgM4ezo0OJPCUN0AOiGo8/edit#heading=h.9iy7nsyi5rzy)

# Configuring RiakCS

1. Run `deploy_proxy` to update Nginx with the new configs to allow webworkers to communicate with RiakCS cluster

2. Install Riak & RiakCS & Stanchion `ansible-playbook deploy_stack.yml --tags=riakcs,stanchion`

3. Setup an admin user
```
ansible-playbook deploy_stack.yml --tags=riakcs-admin-user -e create_admin_user=True
```
When run successfully it should save the keys to the config file. You may need to set that path if the default is not correct. Can be found in `riakcs/defaults/main.yml`

4. Set all the machines to have those keys
```
ansible-playbook deploy_stack.yml --tags=riakcs-admin-keys -e set_admin_keys=True
```
This needs to have `riak_key` and `riak_secret` set in the config files which the previous command should do

5. Join cluster
To join all nodes that haven't been joined with the control machine, run this:
```
ansible-playbook deploy_stack.yml --tags=riakcs-cluster -e join_nodes=True
```
For more finer grain controls checkout `riakcs/tasks/join_nodes.yml`

# Troubleshooting

Riak has particularly painful error messages to debug, here are a few tips and tricks along the way

- A lot of useful log information gets sent to `/var/log/<riak|riakcs|stanchion>/console.log
- Always use IP addresses and not hostnames in conf
- Start machines in this order:
  1. Riak
  2. RiakCS
  3. Stanchion
