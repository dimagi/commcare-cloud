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
fab <env> deploy
```

Sometimes deploys fail intermittently. If a deploy fails, you can resume a deploy by running the following command:

```
fab <env> deploy:resume=yes
```

In the event that a deploy completes successfully and many errors start appearing, you can rollback the release to the previous version:

```
fab <env> rollback
```

### Private releases

The case may arise where you need to setup a new release, but do not want to do a full deploy. For exmample, this is often used when you would want to run a new management command that was just merged. To do this run:
```
fab <env> setup_release
```

This will create a release with the most recent master code and a new virtualenv. Just cd into the directory that is printed on the screen and run your command.

Upon deploys, releases like these are cleaned up by the deploy process. If you know you have a long running command, you can ensure that the release does not get removed by using the `keep_days` option:

```
fab <env> setup_release:keep_days=10
```

This will keep your release around for at least 10 days before it gets removed by a deploy.

### Task list

To get a list of possible tasks to run, use `fab -l`. Here is an abbreviated list of useful commands you can run:

```
clean_releases         Cleans old and failed deploys from the ~/www/<environment>/releases/ directory
deploy                 Preindex and deploy if it completes quickly enough, otherwise abort
force_update_static
hotfix_deploy          deploy ONLY the code with no extra cleanup or syncing
manage                 run a management command
preindex_views         Creates a new release that runs preindex_everything. Clones code from
restart_services
rollback               Rolls back the servers to the previous release if it exists and is same
set_supervisor_config
setup_release          Setup a release in the releases directory with the most recent code.
start_pillows
stop_pillows
supervisorctl
```

## Code architecture

The deploy code attempts to adhere to the following philosophies when adding tasks/functionality to it.

`fab/operations` - These files will include "operations" which are sets of commands to be run on certain machines. You should see `@roles` in these files, but no `@task` decorators.

`fab/fabfile.py` - These should just be tasks. Tasks will be made up of a composition of "operations". Ideally, tasks should never call other tasks.
