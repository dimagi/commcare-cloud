# CommCare-Cloud Changelog

We maintain a changelog in this directory with one YAML file per change.
These files are then compiled into documentation that is made available at
https://dimagi.github.io/commcare-cloud/changelog/.

## Determining whether a change is announce-worthy

Anytime you make a change to commcare-cloud ask yourself these questions:

- Did I need to edit all (or a number of) environments files in conjunction with the code changes?
- Did I need to run commands to deploy it?

If the answer to either is yes, then please complete all of the following steps:

## Creating a changelog entry

- Add an entry to https://github.com/dimagi/commcare-cloud/tree/master/changelog, following the example of other files in that directory
- Run `make` to compile the corresponding docs
- Commit and PR that
- Dimagi-Internal documentation also exists at
  https://confluence.dimagi.com/display/internal/Announcing+changes+affecting+third+parties.
  Notably, the change should be announced on the forum.

### Template

```yaml
title: change title
key: unique-key-for-this-changelog
date:
optional_per_env: [yes/no]
# (optional) Min version of HQ that MUST be deployed before this change can be rolled out (commit hash)
min_commcare_version:
# (optional) Max version of HQ that can be deployed before this change MUST be rolled out (commit hash)
max_commcare_version:
context: |
  Description of the change.
  This will be shown as a sort of "preview" in the index.
  Can be formatted as markdown.

details: |
  Details of the change.
  Can be formatted as markdown.

update_steps: |
  Steps to update.
  Can be formatted as markdown.
```
