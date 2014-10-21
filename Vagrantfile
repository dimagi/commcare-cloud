# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "precise64"

  config.vm.define "app1" do |app1|
    app1.vm.network "private_network", ip: "192.168.33.15"
    app1.vm.provider "virtualbox" do |v|
      v.memory = 768
      v.cpus = 1
    end
    app1.vm.provision "shell", path: "provisioning/nodes.sh"
  end

  # config.vm.define "app2" do |app1|
  #   app1.vm.network "private_network", ip: "192.168.33.18"
  #   app1.vm.provision "shell", path: "provisioning/nodes.sh"
  #   db1.vm.provider "virtualbox" do |v|
  #     v.memory = 768
  #     v.cpus = 1
  #   end
  # end

  config.vm.define "db1" do |db1|
    db1.vm.network "private_network", ip: "192.168.33.16"
    db1.vm.provider "virtualbox" do |v|
      v.memory = 768
      v.cpus = 1
    end
    db1.vm.provision "shell", path: "provisioning/nodes.sh"
  end

  config.vm.define "proxy1" do |proxy1|
    proxy1.vm.network "private_network", ip: "192.168.33.17"
    proxy1.vm.provision "shell", path: "provisioning/nodes.sh"
  end

  config.vm.define "control" do |control|
    control.vm.network "private_network", ip: "192.168.33.14"
    control.vm.provider "virtualbox" do |v|
      v.memory = 768
      v.cpus = 1
    end
    control.vm.provision "shell", path: "provisioning/control.sh"
  end
end
