<!-- This is internal doc for updating these files and is not part of external commcare-cloud docs -->
The dashboard JSON files are obtained by performing relvant datadog API requests.

If they need to be updated, run below to redownload them. `author_name` JSON key is removed since datadog import API doesn't accept that field.

```
# set relevant api keys as env vars and run below
curl -v "https://api.datadoghq.com/api/v1/dashboard/a4u-nfz-gex?api_key=${api_key}&application_key=${application_key}" | sed '/"author_name":/ s/"author_name":[^,]*,//' > mobile-success.json
curl -v "https://api.datadoghq.com/api/v1/dashboard/g9s-pw6-tpg?api_key=${api_key}&application_key=${application_key}" | sed '/"author_name":/ s/"author_name":[^,]*,//' > hq-vitals.json
curl -v "https://api.datadoghq.com/api/v1/dashboard/unt-6cf-nbs?api_key=${api_key}&application_key=${application_key}" | sed '/"author_name":/ s/"author_name":[^,]*,//' > postgres-overview.json
curl -v "https://api.datadoghq.com/api/v1/dashboard/bdu-k5b-bz5?api_key=${api_key}&application_key=${application_key}" | sed '/"author_name":/ s/"author_name":[^,]*,//' > celery.json
curl -v "https://api.datadoghq.com/api/v1/dashboard/hr7-uza-kw5?api_key=${api_key}&application_key=${application_key}" | sed '/"author_name":/ s/"author_name":[^,]*,//' > couchdb.json
```