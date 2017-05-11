# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # config.vm.network :private_network, ip: "192.168.33.99"
  # config.vm.network :forwarded_port, guest: 22, host: 2299

  config.vm.define 'vagrant' do |instance|

    instance.vm.box = 'centos/7'
    # instance.vm.box = 'anandbitra/redhat-6.5'
    # instance.vm.box = 'debian/wheezy64'
    # instance.vm.box = 'debian/jessie64'

    config.vm.provision "ansible" do |ansible|
      ansible.playbook = "tests/test.yml"
      ansible.verbose = 'vv'
      ansible.sudo = true
    end
  end
end
