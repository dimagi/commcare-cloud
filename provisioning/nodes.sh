sudo sed -i 's/^mesg n$/tty -s \&\& mesg n/g' /root/.profile
sudo mkdir -p ~/.ssh
sudo cat /vagrant/provisioning/id_rsa.pub >> ~/.ssh/authorized_keys
