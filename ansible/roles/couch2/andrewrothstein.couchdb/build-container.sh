#!/usr/bin/env bash
docker pull andrewrothstein/docker-ansible-onbuild:ubuntu_trusty
docker build --no-cache=true -t andrewrothstein/ansible-couchdb-container .
