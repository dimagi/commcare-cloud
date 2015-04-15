## Choosing between nginx and Apache

Add change this setting in the config yaml file:
`proxy_type: (apache2|nginx)`

## Adding new nginx sites

* Add a new file in vars/<site_name>
  * Each file here corresponds to an nginx site that will listen on a port/subdomain combination, e.g. slow.commcarehq.com:80
* Add a new line in ../../deploy_proxy.yml
  * `- { role: nginx, when: proxy_type == 'nginx' and active_sites.<site_name> == True, action: site, site_name: <site_name> }`
* Add to the active sites list in the all the config yaml files
  * `<site_name>: True`

### Format of nginx vars file
* file_name: name of site
* listen: 443 ssl or 80
* server_name: subdomain to listen on e.g. slow.commcarehq.org
* location#: Locations define endpoints for incoming requests, read more at http://nginx.org/en/docs/http/ngx_http_core_module.html#location
  * use_balancer: this will proxy requests to the django workers rather than to files on the proxy machine (and load balance requests)
* Other settings can be copied from an existing site in that folder
