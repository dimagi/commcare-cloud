# 12. Generalize load case from fixture feature

**Date:** 2019-02-01

**Optional per env:** No

## CommCare Version Dependency
CommCare versions beyond this commit require this change to function correctly:
[e25dbd4a](https://github.com/dimagi/commcare-hq/commit/e25dbd4aa88523e3913f0acfae7c98e32f4c06c1)


## Change Context
Previously loading a case from a fixture required the fixture to be an attribute.
This change allows using non-attributes from the fixture.

## Details
This migration will require running a management command after deploying.

## Steps to update
After deploying run `./manage.py migrate_load_case_from_fixture.py`. This will
iterate over all applications and builds and update their definitions to the
more generalized form.

Note: if you receive a 413 request entity too large error, you may need to 
increase your environment's
[couchdb2_client_max_body_size](https://github.com/dimagi/commcare-cloud/blob/11312a3083a9535bd433b72cd46c1f021eedd4be/src/commcare_cloud/ansible/group_vars/couchdb2_proxy.yml#L6)
