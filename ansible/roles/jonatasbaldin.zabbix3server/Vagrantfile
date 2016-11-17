# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

  config.vm.define "server" do |server|
      server.vm.box = "ubuntu/trusty64"
      server.vm.hostname = "server"
      server.vm.network "private_network", ip: "192.168.53.10"
  end
 
#  config.vm.define "proxy" do |proxy|
#      proxy.vm.box = "ubuntu/trusty64"
#      proxy.vm.hostname = "proxy"
#      proxy.vm.network "private_network", ip: "192.168.53.11"
#  end

#  config.vm.define "agent" do |agent|
#      agent.vm.box = "ubuntu/trusty64"
#      agent.vm.hostname = "agent"
#      agent.vm.network "private_network", ip: "192.168.53.12"
#  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "tests/test.yml"
    ansible.inventory_path = "tests/inventory"
  end

end
