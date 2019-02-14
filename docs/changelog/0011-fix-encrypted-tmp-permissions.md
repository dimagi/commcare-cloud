# 11. Fix encrypted temp directory permissions

**Date:** 2019-01-16

**Optional per env:** _required on all environments_


## CommCare Version Dependency
This change is not known to be dependent on any particular version of CommCare.


## Change Context
This is a followup to [Added encrypted temporary directory](./0001-add-encrypted-tmp.md)
in which we introduced an encrypted directory for temp files.
In its original implementation, this file was owned by root,
and processes were unable to write to it.

This changes the directory to be owned by cchq, allowing our processes to write to the file.

## Details
The temp folder location will remain at /opt/tmp,
and the retention policy will remain at deleting anything older than 2 days.
The directory, /opt/tmp, will have owner and group cchq,
and as a result any new commcare processes will store temporary files here instead of /tmp/,
realizing the intention of having all tmp files written to a portion of the filesystem
that is encrypted at rest.

## Steps to update
1. Re-initialize the encrypted temp directory:

    ```bash
    commcare-cloud <env> ansible-playbook deploy_commcarehq.yml --tags=ecryptfs
    ```

2. If you haven't followed [Added encrypted temporary directory](./0001-add-encrypted-tmp.md),
    then you'll have to run this as well:

    ```bash
    commcare-cloud <env> update-supervisor-confs
    ```
    If you're sure you've done that already, then you can skip this step.
3. Restart services to have them recognize the change in directory permissions:
    ```bash
    commcare-cloud <env> fab restart_services
    ```
