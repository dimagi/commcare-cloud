#!/usr/bin/env bash

branch=$1

# Restart each couch node with 15 seconds in between
cchq $branch run-shell-command couchdb2 'sleep {{ groups["couchdb2"].index(inventory_hostname) * 15 }}; service couchdb2 restart' -b
