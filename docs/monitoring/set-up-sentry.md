# Set up Sentry for error messages

## Register account on sentry.io

Go to https://sentry.io to create your account.
As of Dec 2018, there's a free tier that allows you to log up to 5k errors a month. 

Sentry allows you to divide your account into multiple "projects".
To log formplayer errors as well, we recommend creating a separate projects
called "commcarehq" and "formplayer". If you'd rather not, it should be possible
to send both errors to the same project.

## Configure for your account
Each account and project on Sentry will come with its own set of
ids and keys, which you'll have to store in vault.yml to configure
the CommCare instance for your account. A complete configuration looks like this:

```yaml
localsettings_private:
  ...
  SENTRY_DSN: 'https://{key}@sentry.io/{project_id}'
  SENTRY_ORGANIZATION_SLUG: 'org slug'
  SENTRY_PROJECT_SLUG: 'project slug'
  # This token is used to create releases and deploys. It needs the 'project:releases' permission.
  SENTRY_API_KEY: '{token}'
  # Repository name for integrating commits into releases
  SENTRY_REPOSITORY: 'dimagi/commcare-hq'
  
  ...
secrets:
  ...
  FORMPLAYER_SENTRY_DSN: 'https://{key}@sentry.io/{project_id}' 
  ...
```

For more details see the [Sentry docs](https://docs.sentry.io/error-reporting/quickstart/?platform=python).
