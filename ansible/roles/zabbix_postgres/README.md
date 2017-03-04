# Manual steps required

In Zabbix UI:

  * Install the PostgreSQL template
    * http://cavaliercoder.com/libzbxpgsql/documentation/template-installation/
    * https://github.com/cavaliercoder/libzbxpgsql/blob/master/templates/Template_PostgreSQL_Server_3.0.xml
  * Update template macro for "Template App PostgreSQL" template:
    * {$PG_CONN} => host=localhost port=5432 user=devreadonly connect_timeout=10
  * Add the pgbouncer template
    * https://github.com/lesovsky/zabbix-extensions/blob/master/files/pgbouncer/pgbouncer-extended-template.xml
