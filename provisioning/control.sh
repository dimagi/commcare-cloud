sudo apt-get update
sudo apt-get install -y python-dev python-pip libffi-dev git

sudo cp /vagrant/provisioning/id_rsa /home/vagrant/.ssh/id_rsa
sudo chown vagrant:vagrant /home/vagrant/.ssh/id_rsa
sudo chmod 400 /home/vagrant/.ssh/id_rsa

ssh-keyscan 192.168.33.15 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.16 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.17 >> /home/vagrant/.ssh/known_hosts

ln -s /vagrant /home/vagrant/commcarehq-ansible
mkdir /home/vagrant/commcare-hq-deploy
sudo pip install virtualenv virtualenvwrapper
sudo -H -u vagrant /vagrant/control/init.sh
echo '[ -t 1 ] && source ~/init-ansible' >> /home/vagrant/.profile

echo "Provision completed! Now ssh into the control box by:

vagrant ssh control
"
