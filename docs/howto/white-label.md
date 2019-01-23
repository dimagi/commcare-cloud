# White label an existing CommCareHQ instance

Describes how to have two URLs point to the same CommCareHQ environment and
serve separate branding for each.

## Customization possible

* Login page can be customized per host with default: `CUSTOM_LANDING_TEMPLATE` in public.yml 
* CommCare HQ name can be customized per host with default: `COMMCARE_HQ_NAME` in public.yml 
* CommCare name can be customized per host with default: `COMMCARE_NAME` in public.yml 
* Error pages can be customized by creating a new branch in our `commcarehq_errors_repository`.
  To reference the new branch specify a new folder and the branch in `reach_errors_home` and `reach_commcare_errors_branch`

## Not supported

* Emails will come from the same addresses
* A user's account will be shared between both URLs
* You cannot limit a domain to only one URL
