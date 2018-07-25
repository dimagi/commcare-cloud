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
git checkout dmr/staging-aws-test
vim environments/staging-aws-test/public.yml
# edit `commcare_cloud_pem: ~/.ssh/g2-access.pem`
```
