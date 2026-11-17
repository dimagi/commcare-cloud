#!/bin/sh
# Fake uv for setup_virtualenv's `uv sync`. Creates a .venv whose python is
# the system python, so manage.py runs through it after the role points its
# shebang at the venv. Appends "uv <args>" to the command log.
set -e
echo "uv $*" >> /var/tmp/deploy_hq-commands.log

if [ "$1" != sync ]; then
  echo "fake uv: unsupported args: $*" >&2
  exit 2
fi
mkdir -p .venv/bin
ln -sf /usr/bin/python3 .venv/bin/python
