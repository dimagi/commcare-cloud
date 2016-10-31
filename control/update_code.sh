#!/bin/bash

function get_branch() {
    git branch | grep '^\*' | sed 's/* //'
}

function abort () {
    echo $1
    echo -e "Aborting."
    exit 1
}

function check_for_changes() {
    branch=$(get_branch)

    if [[ $branch != 'master' ]]
    then
           abort "$1 not on master."
    fi

    changes=$(git diff HEAD)
    if [[ $changes != '' ]]
    then
       abort "$1 has uncommitted changes:\n $changes"
    fi
}

function update_repo() {
    git fetch --prune
    git checkout master
    git reset --hard origin/master
    git submodule update --init --recursive
}

for repo in "commcare-hq-deploy" "commcarehq-ansible/config" "commcarehq-ansible"
do
    cd ~/$repo
    pwd
    check_for_changes $repo
    update_repo
done
