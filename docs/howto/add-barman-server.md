# Add an new Barman node to the exisiting cluster. 
"Barman
Allows your company to implement disaster recovery solutions for PostgreSQL databases with high requirements of business continuity.

Taking an online hot backup of PostgreSQL is now as easy as ordering a good espresso coffee."  ~ https://www.pgbarman.org/

##Before you begin.
Adding a new Barman Server requires following configuration to be done in ansible .

* Add a barman user in the `environments/<env>/vault.yml`
```
POSTGRES_USERS:
    barman:
      username: 'barman_username'
      password: 'barman_secret_password'
```

* Adding a server group (not IP) barman_source group in `environments/<env>/inventory.ini` (It indicates from which servers barman should backup)
```
[pg_barman_source:children]
<db1_group_name>
<db2_group_name>
```

* Adding a barman group in environments/<env>/inventory.ini (It indicates ths server that barman runs on. )
```
[pg_barman]
<barman_server_ip>
```

##Installation: 
**(Do not forget to schedule downtime. )**

* Deploy PostgreSQL server . It does following.

    * Add barman users

    * Change postgresql.conf

    * Change pg_hba.conf to allow barman users

```
user@local$ cchq development ansible-playbook deploy_stack.yml --tags=postgresql --limit=<pg_barman_source>
```

* Deploy Barman

Installs and Configure Barman 
```
user@local$ cchq development ansible-playbook setup_barman.yml 
```

##Troubleshooting 

* Start Wal Shipping.
```
user@local$ cchq development run-shell-command barman "barman switch-wal --force --archive <pg_barman_source_db>"
```

* Check barman status
```bash
user@local$ cchq development run-shell-command barman "barman check <barman_source_db>"
```

## Other useful commands
**Starting Barman**
```bash
barman@backup$ barman receive-wal $db_name #Receive-wal is a foreground process
barman@backup$ barman cron
```

**Stop Barman**
```bash
barman@backup$ barman receive-wal --stop $db_name
```

**List Backups**
```bash
barman@backup$ barman list-backup $db_name  
```

**Delete sepcific backup**
```bash
barman delete $db_name $backup_id
```