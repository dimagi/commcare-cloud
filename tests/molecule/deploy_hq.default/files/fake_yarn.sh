#!/bin/sh
# Fake yarn. Appends "yarn <args>" to the command log for verify to check.
echo "yarn $*" >> /var/tmp/deploy_hq-commands.log
