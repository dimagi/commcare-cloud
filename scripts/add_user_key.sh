#!/bin/bash

function usage()
{
    cat << EOF
usage: $0 [add|remove] options

This script is for adding and removing user keys.

OPTIONS:
   -h       Show this message
   -u       Username of user whose keys is being added or removed
   -f FILE  The public key to be added
EOF
}

if [ "$#" == "0" ]; then
	usage
	exit 1
fi

FUNC='add'
case $1 in
    add|remove)
        FUNC="$1"
        ;;
    *)
        usage
        exit 1
        ;;
esac
shift

KEY=''
USER=''

while getopts "hu:f:" OPTION
do
    case $OPTION in
        h)
            usage
            exit
            ;;
        f)
            KEY="$OPTARG"
            ;;
        u)
            USER="$OPTARG"
            ;;
        ?)
            usage
            exit 1
            ;;
        :)
          echo "Option -$OPTARG requires an argument." >&2
          exit 1
          ;;
    esac
done

if [ -z "$USER" ]; then
    echo "Username required"
    exit 1
fi

ENVS='production staging softlayer swiss'

function add() {
    user=$1
    key_path=$2
    if [ -z "$key_path" ]; then
        echo "Path to public key required"
        exit 1
    fi

    for env in $ENVS; do
        echo "Adding key for $user to $env"
        DEST="ansible/vars/$env/users/${user}_vault.pub"
        cp "$key_path" "$DEST"
        ENV=$env && ansible-vault encrypt --vault-password-file=~/.vault_pass_${ENV}.txt "$DEST"
    done
}

function remove() {
    user=$1
    for env in $ENVS; do
        echo "Removing key for $user from $env"
        KEY_PATH="ansible/vars/$env/users/${user}_vault.pub"
        rm "$KEY_PATH"
    done
}

${FUNC} $USER "$KEY"
