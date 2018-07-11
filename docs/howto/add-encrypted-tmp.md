# How to add encrypted temporary directory
A CommCare deployment uses an encrypted temp directory, which is encrypted by `ecryptfs`.

Configuration of the `encrypted_tmp` directory is an integral part of the `deploy_stack` playbook.
On environments where `encrypted_tmp` is not yet configured, it can be configured by executing the command below.

```bash
commcare-cloud <env> ansible-playbook deploy_stack.yml --tags=ecryptfs
```

## Changelog

13-6-2018 Nitigya Sharma <nsharma@dimagi.com>
* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Create {{encrypted_tmp}} to use for as tmp directory

* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Mount tmp drive

* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Create purging cron jobs for tmp directory

* src/commcare_cloud/ansible/roles/ecryptfs/tasks/main.yml: Drop unencrypted readme in directory
