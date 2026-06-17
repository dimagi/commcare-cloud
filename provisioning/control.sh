sudo apt-get update
sudo apt-get install -y libffi-dev libssl-dev git

ssh-keyscan 192.168.33.15 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.16 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.17 >> /home/vagrant/.ssh/known_hosts
sudo chown vagrant:vagrant /home/vagrant/.ssh/known_hosts

ln -s /vagrant /home/vagrant/commcare-cloud
sudo snap install astral-uv --classic
sudo -H -u vagrant bash -c 'export PATH=/snap/bin:$PATH; NO_INPUT=1 source /vagrant/control/init.sh'

echo "Provision completed! Now ssh into the control box by:

vagrant ssh control
"
