## Set up control machine
```bash
cchq staging-aws-test bootstrap-users --limit control --branch=dmr/staging-aws-test
cchq staging-aws-test ansible-playbook deploy_control.yml --skip-check --branch=dmr/staging-aws-test
scp /Users/droberts/.ssh/g2-access.pem 10.200.20.137:.ssh/
```

## Generate inventory.ini form IP addresses

```bash
pip install awscli
bash environments/staging-aws-test/make-inventory.sh
```

## From control machine...

From control machine
```bash
cchq staging-aws-test ssh control
git checkout dmr/staging-aws-test
git pull  # if you are going back to it
cchq staging-aws-test update-local-known-hosts --branch=dmr/staging-aws-test
cchq staging-aws-test bootstrap-users --limit '!control' --branch=dmr/staging-aws-test
commcare-cloud staging-aws-test deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1' --branch=dmr/staging-aws-test
commcare-cloud staging-aws-test deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1' --branch=dmr/staging-aws-test --start-at-task='PostgreSQL access configuration'
```
