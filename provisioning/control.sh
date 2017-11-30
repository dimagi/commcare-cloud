sudo apt-get update
sudo apt-get install -y python-dev python-pip libffi-dev libssl-dev git

ssh-keyscan 192.168.33.15 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.16 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.17 >> /home/vagrant/.ssh/known_hosts
sudo chown vagrant:vagrant /home/vagrant/.ssh/known_hosts

ln -s /vagrant /home/vagrant/commcarehq-ansible
# Prevent control/init.sh from trying to clone (non-existent) /home/ansible/commcarehq-ansible-secrets.git
mkdir /home/vagrant/commcarehq-ansible/config
# Prevent control/init.sh from trying to clone commcare-hq-deploy
mkdir /home/vagrant/commcare-hq-deploy
sudo pip install virtualenv virtualenvwrapper
sudo -H -u vagrant /vagrant/control/init.sh
echo '[ -t 1 ] && source ~/init-ansible' >> /home/vagrant/.profile

echo "Provision completed! Now ssh into the control box by:

vagrant ssh control
"
