# 1. Added encrypted temporary directory
Date: 2018-06-11

## Status

Accepted

## Context
We consider the privacy and protection of our clients' data, both corporate and personal, to be of the utmost importance and we take robust measures across our business to protect the security and integrity of all such information.

Proceeding further on the same principals we will be encrypting the temporary data used by  CommCare application.



## Decision

We will be adding an encrypted temp directory which will be used to store temporary data of CommCare application. This directory will be encrypted by `ecryptfs`.

Configuration of the encrypted temporary directory will be an integral part of the `deploy_stack` playbook.

On environments where `encrypted_tmp` is not yet configured, it can be configured by executing the command below.

```bash
commcare-cloud <env> ansible-playbook deploy_stack.yml --tags=ecryptfs
```

## Consequences
This will enable the encryption of temporary data on server running CommCare application.

Since, This measure is introduced recently the environments where this has not yet implemented will require to implement the same using the command give above, Though it is a one time effort. 
