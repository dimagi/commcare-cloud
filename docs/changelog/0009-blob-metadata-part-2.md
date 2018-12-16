# Blob Metadata Migration - part 2

This migration will consist of running a series of commands against your cluster
to migrate blob metadata within the form processor SQL database(s).

## Migration steps

Before executing any shell commands, set the `ENV` variable to the name of the
CommCareHQ environment you are migrating.

```sh
ENV=your_environment_name
```

1. Start a new screen session on a server in your cluster:

   ```sh
   cchq $ENV ssh django_manage -t screen -S blobmeta
   ```

   If you get disconnected for any reason, you can reconnect with this command:

   ```sh
   cchq $ENV ssh django_manage -t screen -x blobmeta
   ```

   Do all of the following commands within this screen session

2. Make a backup of all PostgreSQL shard databases (if you have a sharded
   environment) or your main `commcarehq` database in PostgreSQL if your
   environment is not sharded.

3. Run the management command

   ```sh
   sudo -iu cchq
   ENV=your_environment_name
   www/$ENV/current/python_env/bin/python www/$ENV/current/manage.py \
     run_sql simple_move_form_attachments_to_blobmeta --log-output
   ```

   You should see some output similar to this:

   ```
   writing output to file: simple_move_form_attachments_to_blobmeta-2018-12-13T22:05:15.955355.log
   running on default database
   default: processed 1000 items
   ...
   default elapsed: 0:00:46.217034
   default final: processed 12000 items
   ```

   The migration can be run repeatedly if it crashes or must be stopped for any
   reason. Keep running it until you see a `... final: processed ...` message
   for each database.

4. Verify that the migration is complete

   ```sh
   www/$ENV/current/python_env/bin/python www/$ENV/current/manage.py \
     run_sql count_form_attachments --yes
   ```

   You should see output like

   ```
   running on default database
   {'count': 0L}
   (1 rows from default)
   default elapsed: 0:00:01.665248
   ```

   If the number before `L` in `{'count': 0L}` is anything except `0` there
   are more rows to migrate, and you should go back to step 3 and run the
   migration again.

5. If any errors occurred during the migration, please copy the error output
   and submit a bug report. Please include the migration log file (
   `simple_move_form_attachments_to_blobmeta-TIMESTAMP.log`) with your report.
   Do not terminate the screen session until the migration has completed.

6. Exit the screen session when the migration has completed:

   ```sh
   exit  # cchq session
   exit  # screen session
   ```
