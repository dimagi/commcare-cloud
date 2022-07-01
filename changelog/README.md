# CommCare-Cloud Changelog

We maintain a changelog in this directory with one YAML file per change.
These files are then compiled into documentation that is made available at
https://commcare-cloud.readthedocs.io/en/latest/changelog/index.html.

## Determining whether a change is announce-worthy

Anytime you make a change to commcare-cloud ask yourself these questions:

- Did I need to edit all (or a number of) environments files in conjunction with the code changes?
- Did I need to run commands to deploy it?

If the answer to either is yes, then please complete all of the following steps:

## Creating a changelog entry
- Run `manage-commcare-cloud new-changelog <changelog name>`
- Update the changelog content
- Run `make` to compile the corresponding docs
- Commit and PR that
- Dimagi-Internal documentation also exists at
  https://confluence.dimagi.com/display/saas/Announcing+changes+affecting+third+parties.
  Notably, the change should be announced on the forum.
