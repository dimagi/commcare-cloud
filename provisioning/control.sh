snap wait system seed.loaded &
SEED_WAIT_PID=$!
apt-get update
apt-get install -y libffi-dev libssl-dev git

ssh-keyscan 192.168.33.15 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.16 >> /home/vagrant/.ssh/known_hosts
ssh-keyscan 192.168.33.17 >> /home/vagrant/.ssh/known_hosts
chown vagrant:vagrant /home/vagrant/.ssh/known_hosts

# Ensure vagrant UID and GID match host user (for libvirt only)
# OLD and NEW ids match on VirtualBox by default
OLD_UID=$(id -u vagrant)
OLD_GID=$(id -g vagrant)
NEW_UID=$(stat -c '%u' /vagrant)
NEW_GID=$(stat -c '%g' /vagrant)
if [ "$NEW_UID" != "$OLD_UID" ] || [ "$NEW_GID" != "$OLD_GID" ]; then
    sed -i -E "s/^(vagrant:[^:]*):[0-9]+:[0-9]+:/\1:$NEW_UID:$NEW_GID:/" /etc/passwd
    sed -i -E "s/^(vagrant:[^:]*):[0-9]+:/\1:$NEW_GID:/" /etc/group
    chown -R $NEW_UID:$NEW_GID /home/vagrant
fi

# Avoid ansible.log write errors
groupadd dimagidev
usermod --append --groups=dimagidev vagrant
touch /var/log/ansible.log
chgrp dimagidev /var/log/ansible.log
chmod 664 /var/log/ansible.log

# Mount commcare-cloud at the correct location for vagrant user
# Use mount rather than symlink so real paths in ~/commcare-cloud do not resolve to /vagrant
CC_DIR=/home/vagrant/commcare-cloud
sudo -u vagrant mkdir $CC_DIR
mount --bind /vagrant $CC_DIR
grep -E '/vagrant .* bind ' /etc/fstab > /dev/null \
    || echo "/vagrant $CC_DIR none bind 0 0" >> /etc/fstab

# Fake .git dir and pre-commit hook to avoid init.sh and git branch errors
sudo -u vagrant mkdir -p /home/vagrant/.cc-git/hooks
sudo -u vagrant touch /home/vagrant/.cc-git/hooks/pre-commit
mount --bind /home/vagrant/.cc-git $CC_DIR/.git
grep -E '/home/vagrant/.cc-git .* bind ' /etc/fstab > /dev/null \
    || echo "/home/vagrant/.cc-git $CC_DIR/.git none bind 0 0" >> /etc/fstab

# Custom venv because ~/commcare-cloud/.venv may be used by host
echo 'export UV_PROJECT_ENVIRONMENT=~/.cc-venv' >> /home/vagrant/.profile

# Install uv
echo "Waiting for snap seed. This may take a while..."
wait "$SEED_WAIT_PID"
snap install astral-uv --classic

# Initialize commcare-cloud
sudo -iu vagrant bash -c 'NO_INPUT=1 source ~/commcare-cloud/control/init.sh'

echo "Provision completed! Now ssh into the control box by:

vagrant ssh control
"
