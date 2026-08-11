sed -i 's/^mesg n$/tty -s \&\& mesg n/g' /root/.profile

# Create data root so services are able to read the contents.
# Otherwise it is created implicitly, and may not be readable by some services.
mkdir --mode=755 /opt/data

# Elasticsearch's systemd unit doesn't set LimitNPROC, so it inherits the
# system-wide default, which is too low to pass ES's bootstrap max-threads
# check on Vagrant VMs.
sed -i 's/^#\?DefaultLimitNPROC=.*/DefaultLimitNPROC=4096/' /etc/systemd/system.conf
systemctl daemon-reexec
