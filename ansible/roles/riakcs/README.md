# System Overview

For a system overview look [here](https://docs.google.com/document/d/1F5KjtyXmvGcl4nHf6U8_teMgM4ezo0OJPCUN0AOiGo8/edit#heading=h.9iy7nsyi5rzy)

# Configuring RiakCS

1. Run `deploy_proxy` to update Nginx with the new configs to allow webworkers to communicate with RiakCS cluster

2. Deploy Riak & RiakCS & Stanchion `ansible-playbook deploy_stack.yml --tags=riakcs`

# Troubleshooting

Riak has particularly painful error messages to debug, here are a few tips and tricks along the way

- A lot of useful log information gets sent to `/var/log/<riak|riakcs|stanchion>/console.log
- Always use IP addresses and not hostnames in conf
- Start machines in this order:
  1. Riak
  2. RiakCS
  3. Stanchion
