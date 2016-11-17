zabbix3server
=============

Complete installation and configuration of Zabbix 3 Beta Server.

Requirements
------------

This role comes with Apache for webserver and MySQL for database.
If you would like to setup your own webserver and database, be sure to setup the variables correctly.

Role Variables
--------------

### Web

`zabbix3server_web`     
Which webserver to use. For now, just accepts apache.

`zabbix3server_web_install`     
If is False, make sure that you have a working webserver and php, poiting to the directory from `zabbix3server_web_dir` and right frontend files and permissions.

`zabbix3server_web_dir`     
Direcotry that holds Zabbix frontend PHP files.

`zabbix3server_apache_daemon`     
Name of the Apache deamon.

`zabbix3server_apache_user`    
Name of the Apache user.

`zabbix3server_apache_group`    
Name of the Apache group.

`zabbix3server_php_ini_path`    
Path to the php.ini file, if installing a webserver.

`zabbix3server_timezone`    
Timezone to set at PHP ini file.

### Database

`zabbix3server_db`    
Which database to use. For now, just accepts mysql.

`zabbix3server_db_install`    
If is False, make sure that info below connects to a working database loaded with the structure provided by Zabbix.
                                                                          
`zabbix3server_dbhost`    
Host address to the databse.

`zabbix3server_dbname`    
Database name to connect.

`zabbix3server_dbschema`    
Database schema, if needed.

`zabbix3server_dbsocket`    
Database socket, if needed.

`zabbix3server_dbport`    
Database server port to connect.
                                                                          
`zabbix3server_dbrootpassword`    
If installing a dabatase, sets the root password.

`zabbix3server_dbuser`    
If installing a dabatase, sets the user to use.

`zabbix3server_dbuserpassword`    
If installing a dabatase, sets the root password.


### Zabbix

`zabbix3server_betaversion`    
Which beta version will install.

`zabbix3server_downloadurl`    
The URL to download the beta version from SourceForge.

`zabbix3server_compile_options`    
Options to compile Zabbix.

`zabbix3server_install_path`    
Directory to install Zabbix.

**Note: In `defaults/main.yml` file there is a lot of variables, after 'misc'. These variables are discribed in the zabbix_server.conf.j2 file.**

Dependencies
------------

None.

Example Playbook
----------------

This role comes with a Vagrant file. Just fire a `vagrant up` for testing.     
Once the environemnt is up, just run `vagrant provision` or `ansible-playbook -i tests/inventory tests/test.yml`.     
As the date of this commit, the parameter `host_key_checking=False` it's not working. If some SSH connection error occurs, try to execute `export ANSIBLE_HOST_KEY_CHECKING=False`.    

If you want to test the full Zabbix stack (Server, Proxy and Agent), install the other modules with:     
`ansible-galaxy install jonatasbaldin.zabbix3proxy`     
`ansible-galaxy install jonatasbaldin.zabbix3agent`     
And uncomment the sections on the files: `Vagrantfile`, `tests/inventory` and `tests/test.yml`.     

After, login at http://<address>/zabbix with username admin and password zabbix.

License
-------

MIT

Author Information
------------------

Jonatas Baldin      
<mailto:jonatas.baldin@gmail.com>      
http://deployeveryday.com
