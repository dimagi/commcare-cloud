# 3. Implement one command to deploy

Date: 2019-09-05

## Status

Accepted

## Context

During some refactoring of our static file versioning code, there existed several issues which caused static files to be served incorrectly.
These errors propagated in several different ways across the site, but the root issue was always that there was a bug around how JS files were being served.

Full context can be found in the following PRs:

- Initial refactoring: https://github.com/dimagi/commcare-hq/pull/24938
- Failed attempts at fixing `force_update_static`:
    - https://github.com/dimagi/commcare-cloud/pull/3148
    - https://github.com/dimagi/commcare-cloud/pull/3186
- Removal of `hotfix_deploy` and `force_update_static`: https://github.com/dimagi/commcare-cloud/pull/3204
- Simplification of the deploy static file process: https://github.com/dimagi/commcare-hq/pull/25284

## Decision

We are removing the previous commands `hotfix_deploy` and `force_update_static`.
Any future deploys must go through `commcare-cloud <env> deploy`

## Consequences

The `hotfix_deploy` command skipped over some unnecessary steps when deploying python only changes.
This resulted in a somewhat faster deploy for urgent tasks.
Since `hotfix_deploy` was originally implemented, many changes to our deploy process have been implemented that have made our standard deploy process faster and more stable than before.

If we find that faster deploys are a necessity, we will invest in improving our standard deploy process.
This may include, but not limited to:
- Batching restarts of our webworkers at the end of the deploy
- If no static files have changed since last deploy, skipping collect_static and other tasks
- If no couch views have been changed, skipping syncing couch views
- If no migrations have been introduced, skipping any migrations checks
- If no dependency files have changed skip `pip install`, `bower update` etc
