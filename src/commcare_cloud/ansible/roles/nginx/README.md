### Format of nginx vars file
Under `nginx_sites` you have a list of objects with the single key `server`
set to an object with the following properties:
* `file_name`: name of site file to be used in sites-available/sites-enabled
* `listen`: `'443 ssl'` or `'80'`
* `server_name`: subdomain to listen on e.g. `'slow.commcarehq.org'`
* `locations`: Locations define endpoints for incoming requests, read more at http://nginx.org/en/docs/http/ngx_http_core_module.html#location
  * `balancer`: this will proxy requests to the group defined rather than to files on the proxy machine (and load balance requests).
    E.g. `balancer: webworkers` will proxy requests to the django machines
* Other settings can be copied from an existing site in that folder
