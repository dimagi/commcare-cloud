# Set up SMTP services to send emails

To enable sending emails from your instance you will need an SMTP service (e.g. Amazon SES or other).

You will need to change the following items

**public.yml**
```yaml
server_email: "server@example.com" # an email address you can send from
default_from_email: "server+noreply@example.com" # an email address you can send from
support_email: "support@project.example.com" # email address you can receive support requests to

localsettings:
  EMAIL_SMTP_HOST:"smtp.yourorg.org" # SMTP host provided by your service
  EMAIL_SMTP_PORT: 25
  EMAIL_USE_TLS: yes  # if your SMTP host requires TLS
```

You will also need to modify the login and password in the vault.

```bash
$ ansible-vault edit ~/environments/monolith/vault.yml
```

**vault.yml**
```yaml
localsettings_private:
    EMAIL_LOGIN: ''
    EMAIL_PASSWORD: ''
```


After editing those files you will need to update the config and restart services:
```bash
$ commcare-cloud <env> update-config
$ commcare-cloud <env> fab restart_services
```

You can then test your email settings worked by running:
```bash
$ commcare-cloud <env> django-manage send_email --subject=test --recipients="youremail@example.com" "This is a test message"
```

If everything worked, it should send without error.
