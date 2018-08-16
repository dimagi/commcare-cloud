# Configure a firewall on the servers
In situations where the servers are not behind a spearate firewall it is
necessary to run a firewall service on the each server to lock down access
to unprotected services.

If you are unsure whether this is an issue or not you can try to access
some of the services directly (replace <commcare.mysite.com> with the address of your
CommCare instance):

**Celery Flower**: https://<commcare.mysite.com>:5555
**Elasticsearch**: https://<commcare.mysite.com>:9200

If either of those URLs work then you need a firewall.

## Configuration
This setup uses [ufw](https://wiki.ubuntu.com/UncomplicatedFirewall).

In order to configure the firewall you need to determine what network
interfaces your servers have. There must be two interfaces, one for secure
traffic and one for insecure traffic.

The public IP address of the proxy server should be connected to one of these
interfaces.

In the example below `eth0` is the private interface and `eth1` is the public:

* Server1:
  * eth0: 172.16.23.1
  * eth1: 213.55.85.200
* Server2:
  * eth0: 172.16.23.2
  
To configure the firewall for this setup add the following to your environment's
`public.yml` file:

```
ufw_private_interface: eth0
```

Now run the following command:
*(before you run this make sure you have access to your servers in case you get locked out)*

```
$ commcare-cloud <env> ansible-playbook deploy_common.yml --tags ufw-proxy,ufw
```

This will apply the following rules:

**proxy**
    
    allow 443 in (https)
    allow 80 in (http)
    allow 22 in (ssh)
    allow 60000:61000 in (mosh)
    allow all in on <ufw_private_interface>
    block all in
    
**all other servers**
    
    allow all in on <ufw_private_interface>
    block all in
