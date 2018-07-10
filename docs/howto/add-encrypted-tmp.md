# How to add encrypted temporary directory
CCHQ deployment uses encrypted temporary directory. which is encrypted by `ecryptfs`

configuration of `encrypted_tmp` directory is integral part of the `deploy_stack` playbook.
Environments where `encrypted_tmp` is not configured can be configured by executing the command below.

```bash
commcare-cloud <env> ansible-playbook deploy_stack.yml --tags=ecryptfs
```

## Changelog

13-6-2018 Nitigya Sharma <nsharma@dimagi.com>
* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Create {{encrypted_tmp}} to use for as tmp directory

* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Mount tmp drive

* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Create purging cron jobs for tmp directory

* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Drop unencrypted readme in directory
