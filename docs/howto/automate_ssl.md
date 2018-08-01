# How to automate LetsEncrypt SSL certificate renewal
This document details about "_How to switch from third party SSL to LetsEncrypt SSL_". 

If you are searching for document to configure letsencrypt in a new environment, please refer [Enable HTTPS](https://github.com/dimagi/commcare-cloud/blob/master/docs/howto/enable-https.md)  

Presently we are using a combination of ansible and Certbot to renew our Letsencrypt certificates.
Ansible is used to configure the Nginx and Certbot.
Afterwards Certbot is used for the certificate automation. 

### Use of Ansible
* Installation and configuration of Certbot.
* Configure Nginx configuration files.
* Creation of directories used for http-01 challenge.
* Creating links to Certbot's fullchain.pem and privkey.pem files
    
### Use of Certbot
* Getting certificate for the first time.
* Renewal of certificate 1 month before the expiry.
* Moving symlinks to latest certificate and private key.

### Monitoring
The expiry of certificates is monitored via external monitoring tools.

---

## How to configure in environment which are already using some third party SSL Certificate.

*Assumption:* Following variables are predefined

* ENV_SITE_HOST: Site for which certificate is renewed
* ssl_keys_dir: Directory to keep ssl certificate and keys links for nginx.

To setup the automate renewal we can use commcare-cloud command after making following changes.
* Add `letsencrypt_cchq_ssl: True` variable in `proxy.yml` to enable the use of letsencrypt tasks. 

* Add the following tasks to create symlink to `privkey.pem` and `fullchain.pem` in `src/commcare_cloud/ansible/roles/nginx/tasks/install.yml`


```
name: Link ENV SSL cert
  become: yes
  file:
  src: "/etc/letsencrypt/live/{{ENV_SITE_HOST}}/fullchain.pem"
  dest: "{{ ssl_certs_dir }}/{{ env_nginx_ssl_cert }}"
  state: link
when: not fake_ssl_cert and ENV_SITE_HOST | default(None)

name: Link ENV SSL Key
  become: yes
  file:
    src: "/etc/letsencrypt/live/{{ENV_SITE_HOT}}/privkey.pem"
    dest: "{{ ssl_keys_dir }}/{{ env_nginx_ssl_key  }}"
    state: link

  when: not fake_ssl_cert and ENV_SITE_HOST | default(None)


```

Once we have added the configuration for the new environment. we can proceed with deploying the same using

```
commcare-cloud <env> ansible-playbook deploy_proxy.yml
```
