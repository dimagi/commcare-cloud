#!/usr/bin/env bash

# This script just aims to provide a way for ansible-vault to read standard input.
# ansible-vault doesn't let you specify passwords on the command line -- you either
# need to provide a password file or a password script. This functions as the latter,
# reading passwords piped in
read -r line
echo "$line"
