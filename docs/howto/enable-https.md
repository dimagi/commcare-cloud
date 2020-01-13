# How to Enable HTTPS with letsencrypt

Nearly the entire process of setting up a production commcarehq instance
is fully automated. One area that still requires some manual intervention
is setting up certificates for HTTPS.

Here are the manual steps required.

<small>**Note from author**: I haven't tried this many times in a row and noted/fixed all the kinks,
so there may be something missing here,
but those are the general steps at this point.
It would be lovely to make it so that it happened on the first setup,
but we're not quite there yet.
If there are any errors or gaps, a github issue or pull requests
would be much appreciated.</small>

## 1. Set up site without HTTPS

In `proxy.yml`:
- make sure `fake_ssl_cert: yes`

and run full stack deploy

```bash
commcare-cloud <env> bootstrap-users
commcare-cloud <env> deploy-stack --skip-check -e 'CCHQ_IS_FRESH_INSTALL=1'
commcare-cloud <env> deploy commcare --set ignore_kafka_checkpoint_warning=true
```

Note: if you already have a running site with a previous cert,
you can just skip this step.

## 2. Request a letsencrypt cert

Run the playbook to request a letsencrypt cert:
```bash
cchq <env> ansible-playbook letsencrypt_cert.yml --skip-check
```

## 3. Update settings to take advantage of new certs

In `proxy.yml`:
- set `fake_ssl_cert` to `no`
- set `nginx_combined_cert_value` and `nginx_key_value` to `null`
  (or remove them)

and deploy proxy again.

```bash
cchq <env> ansible-playbook deploy_proxy.yml 
```
