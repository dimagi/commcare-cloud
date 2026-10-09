#!/bin/sh
# Fake for amazon-kinesis-agent's `./setup --install`, which builds the agent
# from source and downloads its Java dependencies. This only creates what the
# role relies on afterwards: the agent user, /etc/aws-kinesis and the service.
set -e

if [ "$*" != "--install" ]; then
  echo "fake setup: unsupported args: $*" >&2
  exit 2
fi

getent passwd aws-kinesis-agent-user >/dev/null ||
  useradd --system --user-group --no-create-home \
    --shell /usr/sbin/nologin aws-kinesis-agent-user

mkdir -p /etc/aws-kinesis

cat > /usr/bin/start-aws-kinesis-agent <<'EOF'
#!/bin/sh
exec sleep infinity
EOF
chmod 0755 /usr/bin/start-aws-kinesis-agent

cat > /etc/systemd/system/aws-kinesis-agent.service <<'EOF'
[Unit]
Description=Fake Amazon Kinesis Agent (Molecule stub)

[Service]
User=aws-kinesis-agent-user
ExecStart=/usr/bin/start-aws-kinesis-agent
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
