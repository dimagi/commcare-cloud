# CommCare-Cloud Changelog

We maintain a changelog in this directory with one YAML file per change.
These files are then compiled into documentation that is made available at
https://dimagi.github.io/commcare-cloud/changelog/.

Dimagi-Internal documentation also exists at
https://confluence.dimagi.com/display/internal/Announcing+commcare-cloud+changes.

## Determining whether a change is announce-worthy

Anytime you make a change to commcare-cloud ask yourself these questions:

- Did I need to edit all (or a number of) environments files in conjunction with the code changes?
- Did I need to run commands to deploy it?

## Creating a changelog entry
If the answer to either is yes, then please complete all of the following steps:

- Add an entry to https://github.com/dimagi/commcare-cloud/tree/master/changelog, following the example of other files in that directory
- Run `make` to compile the corresponding docs
- Commit and PR that
