# Test Cloud Container Automation

Orchestrate containers for local testing of things like Ansible playbooks.

## Usage

```sh
export COMMCARE_CLOUD_ENVIRONMENTS=tests/cloud/environments
export TEST_CLOUD_WORKERS=7
alias sail=`pwd`/tests/cloud/sail.py
sail --help  # optional

# build and start test containers
sail up

# run commcare-cloud commands to interact with the containers
cchq test ssh admin@django_manage

# tear down test containers
sail down
```

The "admin" user's password is "cloud", although it should not be needed if
your SSH public key is located at ``~/.ssh/id_rsa.pub`` or if the
``TEST_CLOUD_AUTHORIZED_KEYS`` environment variable is configured to point
to a file containing your public key.

Test environment configuration is located in ``tests/cloud/environments/test``.

The ``tests/cloud`` directory can be copied to a directory outside of version
control (and environment variables adjusted accordingly) for experimentation
and customization.
