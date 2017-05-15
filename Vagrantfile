# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.require_version ">= 1.7.0"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"
  config.ssh.insert_key = false

  config.vm.define "monolith" do |monolith|
    monolith.vm.hostname = "monolith"
    monolith.vm.network "private_network", ip: "192.168.33.21"
    monolith.vm.provider "virtualbox" do |v|
      v.memory = 768
      v.cpus = 1
    end
    monolith.vm.provision "shell", path: "provisioning/nodes.sh"
    monolith.vm.network "forwarded_port", guest: 5000, host: 5000
    monolith.vm.network "forwarded_port", guest: 5984, host: 5984
    monolith.vm.network "forwarded_port", guest: 5986, host: 5986
  end

  config.vm.define "control" do |control|
    control.vm.hostname = "control"
    control.vm.network "private_network", ip: "192.168.33.20"
    control.vm.provider "virtualbox" do |v|
      v.memory = 768
      v.cpus = 1
    end
    control.vm.provision "shell", path: "provisioning/control.sh"
  end
end
