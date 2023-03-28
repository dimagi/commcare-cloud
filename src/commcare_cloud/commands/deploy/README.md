## Deploy Architecture

### Overview

The deploy utilizes symlinks to implement an atomic deploy. This means that during a deploy, we have a folder to build up a release candidate. When that deploy succeeds, we symlink to that release and the webworkers work off that.

In HQ it's implemented with a `releases` folder. In the `releases` folder, there will be another folder with the actual release. An example release will look something like this:
```
www/<env>/releases/2015-09-10_04.00
```
The symlinked directory will be under `current`. 
```
www/<env>/current -> www/<env>/releases/2015-09-10_04.00
```

### Server layout

```
    ~/www/
        This folder contains the code, python environment, and logs
        for each environment (staging, production, etc) running on the server.
        Each environment has its own subfolder named for its evironment
        (i.e. ~/www/staging/log and ~/www/production/log).

    ~/www/<environment>/releases/<YYYY-MM-DD-HH.SS>
        This folder contains a release of commcarehq. Each release has its own
        virtual environment that can be found in `python_env`.

    ~/www/<environment>/current
        This path is a symlink to the release that is being run
        (~/www/<environment>/releases<YYYY-MM-DD-HH.SS>).

    ~/www/<environment>/current/services/
        This contains two subfolders
            /supervisor/
        which hold the configurations for these applications
        for each environment (staging, production, etc) running on the server.
        Theses folders are included in the global /etc/apache2 and
        /etc/supervisor configurations.

```

## Deploying tips & tricks

### Deploying

To initiate a regular deploy, use the following command:

```
cchq <env> [--control] deploy
```

Sometimes deploys fail intermittently. If a deploy fails, you can resume a deploy by running the following command:

```
cchq <env> [--control] deploy --resume=RELEASE_NAME
```

In the event that a deploy completes successfully and many errors start appearing, you can rollback the release to the previous version:

```
cchq <env> deploy --resume=PREVIOUS_RELEASE
```

### Private releases

The case may arise where you need to setup a new release, but do not want to do a full deploy. For example, this is often used when you would want to run a new management command that was just merged. To do this run:
```
cchq <env> deploy commcare --private
```

This will create a release with the most recent master code and a new virtualenv. Just cd into the directory that
is printed on the screen and run your command, or use `django-manage` with the `--release=<NAME>` parameter.

To set up a release based on a non-master branch, run:

```
cchq <env> deploy commcare --private --commcare-rev=<HQ BRANCH>
```

Upon deploys, releases like these are cleaned up by the deploy process. If you know you have a long running command, you can ensure that the release does not get removed by using the `--keep-days` option:

```
cchq <env> deploy commcare --private --keep-days=10
```

This will keep your release around for at least 10 days before it gets removed by a deploy.

### Task list

The `fab` command is now obsolete. Many of its sub-commands have been replaced with new commands:

```
Obsolete fab command        Replaced by 'commcare-cloud <env> ...'
--------------------        --------------------------------------
check_status                ping all
                            service postgresql status
                            service elasticsearch status

clean_releases              clean-releases [--keep=N]
deploy_commcare             deploy commcare
kill_stale_celery_workers   kill-stale-celery-workers
manage                      django-manage
perform_system_checks       perform-system-checks
preindex_views              preindex-views
restart_services            service commcare restart
restart_webworkers          service webworker restart
rollback                    deploy commcare --resume=PREVIOUS_RELEASE
rollback_formplayer         ansible-playbook rollback_formplayer.yml --tags=rollback
setup_limited_release       deploy commcare --private [--keep-days=N] [--commcare-rev=HQ_BRANCH]
setup_release               deploy commcare --private --limit=all [--keep-days=N] [--commcare-rev=HQ_BRANCH]
start_celery                service celery start
start_pillows               service pillowtop start
stop_celery                 service celery stop
stop_pillows                service pillowtop stop
supervisorctl               service NAME ACTION
update_current              deploy commcare --resume=RELEASE_NAME
```
