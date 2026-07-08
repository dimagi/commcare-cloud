# -*- mode: ruby -*-
# vi: set ft=ruby :

# VirtualBox is the default provider, and does not require any special set up.
#
# libvirt host set up
#
# 1. Create "cchq" storage pool
#
#   COMMCARE_CLOUD_LIBVIRT_POOL=cchq
#   COMMCARE_CLOUD_LIBVIRT_DIR=/path/to/libvirt-cchq  # >35G disk space required full deploy-stack
#   mkdir $COMMCARE_CLOUD_LIBVIRT_DIR
#   virsh --connect qemu:///session pool-define-as $COMMCARE_CLOUD_LIBVIRT_POOL \
#     dir --target $COMMCARE_CLOUD_LIBVIRT_DIR
#   virsh --connect qemu:///session pool-build $COMMCARE_CLOUD_LIBVIRT_POOL
#   virsh --connect qemu:///session pool-start $COMMCARE_CLOUD_LIBVIRT_POOL
#   virsh --connect qemu:///session pool-autostart $COMMCARE_CLOUD_LIBVIRT_POOL
#
#   # assign SELinux tags if your system requires that
#   COMMCARE_CLOUD_DIR=~/commcare-cloud
#   sudo semanage fcontext -a -t svirt_home_t "$COMMCARE_CLOUD_LIBVIRT_DIR(/.*)?"
#   sudo semanage fcontext -a -t svirt_home_t "$COMMCARE_CLOUD_DIR(/.*)?"
#   sudo restorecon -Rv $COMMCARE_CLOUD_LIBVIRT_DIR $COMMCARE_CLOUD_DIR
#
# 2. Configure "libvirt-cchq" network
#
#   sudo nmcli connection add type bridge ifname libvirt-cchq con-name libvirt-cchq \
#     ipv4.method manual ipv4.addresses 192.168.33.1/24 ipv6.method disabled
#   sudo nmcli connection up libvirt-cchq
#   echo "allow libvirt-cchq" | sudo tee -a /etc/qemu/bridge.conf
#
# 3. Configure environment and start VMs
#
#   vagrant up --provider=libvirt

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.require_version ">= 1.7.0"

require_relative './provisioning/key_authorization'


Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "generic/ubuntu2204"
  config.vm.provider "libvirt" do |v|
    v.storage_pool_name = ENV.fetch("COMMCARE_CLOUD_LIBVIRT_POOL", "cchq")
    v.qemu_use_agent = true
  end

  config.ssh.insert_key = false
  authorize_key config, '~/.vagrant.d/insecure_private_key'

  {
    'control' => ['192.168.33.14', 'control'],
    'app1'    => ['192.168.33.15', 'nodes'],
    'db1'     => ['192.168.33.16', 'nodes'],
    'proxy1'  => ['192.168.33.17', 'nodes'],
  }.each do |short_name, (ip, type)|
    config.vm.define short_name do |host|
      host.vm.hostname = "#{short_name}.hq.dev"
      host.vm.provision "shell", path: "provisioning/#{type}.sh"

      host.vm.provider "virtualbox" do |v, override|
        v.memory = 768
        v.cpus = 1
        override.vm.network "private_network", ip: ip
      end

      host.vm.provider "libvirt" do |v, override|
        v.memory = 768
        v.cpus = 1
        override.vm.network "public_network", ip: ip,
          dev: "libvirt-cchq", type: "bridge", auto_config: true

        if short_name == 'control'
          override.vm.synced_folder ".", "/vagrant", type: "9p", accessmode: "mapped"
        end
      end

    end
  end
end
