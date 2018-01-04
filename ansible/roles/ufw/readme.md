# UFW Module

This module configures a simple firewall rule using [ufw](https://wiki.ubuntu.com/UncomplicatedFirewall).

To enable it just specify a `ufw_private_interface` (e.g. `eth0`) in your environment variables.
If you do this, inbound traffic on _all interfaces except that one_ will be blocked.
This includes ssh access so be careful in setting this up!
