sed -i 's/^mesg n$/tty -s \&\& mesg n/g' /root/.profile

# Create data root so services are able to read the contents.
# Otherwise it is created implicitly, and may not be readable by some services.
mkdir --mode=755 /opt/data
