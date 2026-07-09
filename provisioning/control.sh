apt-get update
apt-get install -y libffi-dev libssl-dev git

ssh-keyscan 192.168.33.15 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.16 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.17 >> /home/vagrant/.ssh/known_hosts
chown vagrant:vagrant /home/vagrant/.ssh/known_hosts

touch /var/log/ansible.log
chown vagrant:vagrant /var/log/ansible.log

# NOTE: if the UID of the host user is not 1000 (matching the vagrant
# user's UID) then commcare-cloud files may not be writable.
# Always edit files on the host rather than in the guest VM.
CC_DIR=/home/vagrant/commcare-cloud
sudo -u vagrant mkdir $CC_DIR
mount --bind /vagrant $CC_DIR

# fake pre-commit hook to avoid error in init.sh
sudo -u vagrant mkdir -p /home/vagrant/.cc-hooks
sudo -u vagrant cp $CC_DIR/git-hooks/pre-commit.sh /home/vagrant/.cc-hooks/pre-commit
mount --bind /home/vagrant/.cc-hooks $CC_DIR/.git/hooks

# custom venv because ~/commcare-cloud/.venv may be used by host
echo 'export UV_PROJECT_ENVIRONMENT=~/.cc-venv' >> /home/vagrant/.profile

snap install astral-uv --classic

sudo -iu vagrant bash -c 'NO_INPUT=1 source ~/commcare-cloud/control/init.sh'

echo "Provision completed! Now ssh into the control box by:

vagrant ssh control
"
