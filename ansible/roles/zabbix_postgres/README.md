# Manual steps required

In Zabbix UI:

  * Update template macro for "Template App PostgreSQL" template:
    * {$PG_CONN} => host=localhost port=5432 user=devreadonly connect_timeout=10
