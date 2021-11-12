
Set up Sentry for error logs
============================

Register account on sentry.io
-----------------------------

Go to `sentry.io <https://sentry.io>`_ to create your account.

As of Dec 2018, there's a free tier that allows you to log up to 5k errors a month. 

Sentry allows you to divide your account into multiple "projects".
To log formplayer errors as well, we recommend creating a separate projects
called "commcarehq" and "formplayer". If you'd rather not, it should be possible
to send both errors to the same project.

Configure for your account
--------------------------

Each account and project on Sentry will come with its own set of
IDs and keys, which you'll have to store in the environment configuration failes.
A complete configuration looks like this:

**public.yml**

.. code-block:: yaml

   localsettings:
     SENTRY_ORGANIZATION_SLUG: 'organization slug'
     SENTRY_PROJECT_SLUG: 'commcare project slug'
     # Repository name for integrating commits into releases
     SENTRY_REPOSITORY: 'dimagi/commcare-hq'

**vault.yml**

.. code-block:: yaml

   localsettings_private:
     SENTRY_DSN: 'https://{key}@sentry.io/{project_id}'
     # This token is used to create releases and deploys. It needs the 'project:releases' permission.
     SENTRY_API_KEY: '{token}'

     ...
   secrets:
     FORMPLAYER_SENTRY_DSN: 'https://{key}@sentry.io/{project_id}' 
     ...

For more details see the `Sentry docs <https://docs.sentry.io/error-reporting/quickstart/?platform=python>`_.
