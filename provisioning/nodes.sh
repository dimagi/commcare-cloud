sudo sed -i 's/^mesg n$/tty -s \&\& mesg n/g' /root/.profile
sudo cat /vagrant/provisioning/id_rsa.pub >> /home/vagrant/.ssh/authorized_keys
