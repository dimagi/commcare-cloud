# 13. Java upgrade for formplayer

**Date:** 2019-02-11

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
Previously, Formplayer was running on Java 7.
This change updates us to Java 8 for formplayer.

## Details
This only affects the machine that formplayer is on.
If formplayer is installed on a machine with other Java processes,
all Java processes on that machine will now be using Java 8 as well.
We expect this to work without issue either way.

## Steps to update

1. Install the java 8 on formplayer server

    ```
    commcare-cloud <env> ap deploy_formplayer.yml --limit=formplayer
    ```

2. Restart the all java processess on formplayer server to take the latest java changes.
    To see a full list of processes using java, run.

    ```
    ps -ef | grep java
    ```
    Then for each one, use `service ... restart` to restart the process.
