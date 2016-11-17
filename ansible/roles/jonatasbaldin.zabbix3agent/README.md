zabbix3agent
=============

Complete installation and configuration of Zabbix 3 Beta Agent.

Requirements
------------

None.

Role Variables
--------------

### Zabbix

`zabbix3agent_betaversion`    
Which beta version will install.

`zabbix3agent_downloadurl`    
The URL to download the beta version from SourceForge.

`zabbix3agent_compile_options`    
Options to compile Zabbix.

`zabbix3agent_install_path`    
Directory to install Zabbix.

`zabbix3agent_server`    
Server address that proxy is poiting to.

**Note: In `defaults/main.yml` file there is a lot of variables, after 'misc'. These variables are discribed in the zabbix_agent.conf.j2 file.**

Dependencies
------------

None.

Example Playbook
----------------

This role comes with a Vagrant file. Just fire a `vagrant up` for testing.     
Once the environemnt is up, just run `vagrant provision` or `ansible-playbook -i tests/inventory tests/test.yml`.     
As the date of this commit, the parameter `host_key_checking=False` it's not working. If some SSH connection error occurs, try to execute `export ANSIBLE_HOST_KEY_CHECKING=False`.    

If you want to test the full Zabbix stack (Server, Proxy and Agent), install the other modules with:     
`ansible-galaxy install jonatasbaldin.zabbix3server`     
`ansible-galaxy install jonatasbaldin.zabbix3proxy`     
And uncomment the sections on the files: `Vagrantfile`, `tests/inventory` and `tests/test.yml`.     

License
-------

MIT

Author Information
------------------

Jonatas Baldin      
<mailto:jonatas.baldin@gmail.com>      
http://deployeveryday.com
