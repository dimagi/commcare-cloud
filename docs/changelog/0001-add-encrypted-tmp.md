# 1. Added encrypted temporary directory

**Date:** 2018-06-11

**Optional per env:** No

**Dependant CommCare version:** None

## Change Context
Some of the CommCare processes make use of temporary files to store client data (such as data exports) so in order to keep that data protected we have modified the setup to use an encrypted temporary directory.

## Details

Temp folder location: /opt/tmp

Retention policy: Delete files older than 2 days

## Steps to update

1. Create the encrypted temporary directory

```bash
commcare-cloud <env> ansible-playbook deploy_commcarehq.yml --tags=ecryptfs
```

2. Update the CommCare process configuration to use the encrypted temporary directory

```bash
commcare-cloud <env> update-supervisor-confs
```
