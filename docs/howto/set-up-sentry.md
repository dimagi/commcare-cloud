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
  # Found at https://sentry.io/settings/{org}/commcarehq/keys/ under DSN (Deprecated)
  # https://{SENTRY_PUBLIC_KEY}:{SENTRY_PRIVATE_KEY}@sentry.io/{SENTRY_PROJECT_ID}
  SENTRY_PUBLIC_KEY: '2fba92899ed1541b5333885f4da56f92'
  SENTRY_PRIVATE_KEY: 'c9a986fed5b746f265d69c16257d8961'
  SENTRY_PROJECT_ID: '793624'
  # Set to 'https://sentry.io/{org}/commcarehq/?query='
  SENTRY_QUERY_URL: 'https://sentry.io/myorg/commcarehq/?query='
  # Create this at https://sentry.io/settings/account/api/auth-tokens/
  SENTRY_API_KEY: '382b0721626e4f109ecc79689aa3878c7fa905dd518ea316b742eeeb696f9638'
  ...
secrets:
  ...
  # Found at https://sentry.io/settings/{org}/formplayer/keys/ under DSN (Deprecated)
  FORMPLAYER_SENTRY_DSN: 'https://174808d807d7f00b9eef3e9eb07909ff:f94747f5def308ff266d2b411bef0994@sentry.io/262831' 
  ...
```

(All keys in this example were randomly generated for this purpose
and are not real for any actual sentry account.)

In this example, commcarehq and formplayer have different sentry projects,
with the commcarehq sentry project's keys going into `localsettings_private.SETNRY_*`,
and formplayer sentry project's keys going into `secrets.FORMPLAYER_SENTRY_DSN`
(in a url format that they provide and call the DSN, or Data Source Name).
