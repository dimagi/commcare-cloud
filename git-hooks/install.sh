#!/bin/bash

function usage()
{
    cat << EOF
usage: $0 options

This script installs git hooks

OPTIONS:
   -h      Show this message
   -f      don't ask before overwriting your current git hooks
   -r      remove existing hooks but do not add the new ones
EOF
}

OPT='-i'
FUNC='link_hooks'

while getopts "hfr" OPTION
do
    case $OPTION in
        h)
            usage
            exit
            ;;
        f)
            OPT='-f'
            ;;
        r)
            FUNC='remove_hooks'
            ;;
        ?)
            usage
            exit 1
            ;;
    esac
done

function link_hooks() {
    hook=$1
    base_path=$2
    ln -s -f $OPT ../../git-hooks/$hook.sh $base_path/hooks/$hook
}

function remove_hooks() {
    hook=$1
    base_path=$2
    rm $OPT $base_path/hooks/$hook
}

${FUNC} 'pre-commit' '.git'
