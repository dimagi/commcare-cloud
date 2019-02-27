# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.require_version ">= 1.7.0"

require_relative './provisioning/key_authorization'


Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/bionic64"
  cchq_proxy_port = ENV.fetch("VAGRANT_CCHQ_PROXY_PORT", 8080)
  config.ssh.insert_key = false
  authorize_key config, '~/.vagrant.d/insecure_private_key'

  {
    'app1'    => '192.168.33.15',
    'db1'   => '192.168.33.16',
    'citusdb0' => '192.168.33.30',
    'citusdb1'   => '192.168.33.31',
    'citusdb2'   => '192.168.33.32',
    'citusdb3'   => '192.168.33.33',
    'proxy1' => '192.168.33.17',
  }.each do |short_name, ip|
    config.vm.define short_name do |host|
      host.vm.network 'private_network', ip: ip
      host.vm.hostname = "#{short_name}.hq.dev"
      host.vm.provision "shell", path: "provisioning/nodes.sh"
      host.vm.provider "virtualbox" do |v|
        v.memory = 768
        v.cpus = 1
      end
    end
  end

  config.vm.define "control" do |host|
    host.vm.hostname = "control"
    host.vm.network "private_network", ip: "192.168.33.14"
    host.vm.hostname = "control.hq.dev"
    host.vm.provider "virtualbox" do |v|
      v.memory = 768
      v.cpus = 1
    end
    host.vm.provision "shell", path: "provisioning/control.sh"
  end
end
