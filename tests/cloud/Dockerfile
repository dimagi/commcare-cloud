FROM ubuntu:22.04
RUN apt update && \
    apt upgrade -y && \
    apt install sudo -y && \
    apt install acl iproute2 openssh-server python3-apt python3-pip rsyslog vim -y && \
    rm /sbin/init  # prevent ansible_service_mgr=systemd
RUN useradd -ms /bin/bash -u 1000 admin && \
    useradd -ms /bin/bash -u 1001 cchq && \
    echo '%admin ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    echo 'admin:cloud' | chpasswd && \
    mkdir -m700 /home/admin/.ssh && \
    ln -s /run/secrets/authorized_keys /home/admin/.ssh/authorized_keys && \
    chown -R admin:admin /home/admin/.ssh

# Ubuntu in docker uses sysv (not systemd). This works because commcare-cloud
# removes /etc/init.d/supervisor but not /etc/init.d/supervisord
COPY --chmod=755 supervisord.init.sh /etc/init.d/supervisord

EXPOSE 22
CMD ["/bin/bash", "-c", "service ssh start; sleep infinity"]
