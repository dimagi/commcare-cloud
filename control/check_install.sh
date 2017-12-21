#!/usr/bin/env bash

function realpath() {
    python -c "import os,sys; print os.path.realpath(sys.argv[1])" $1
}

ANSIBLE_REPO="$(realpath $(dirname $0)/..)"
FAB_CONFIG="${ANSIBLE_REPO}/fab/fab/config.py"

[ ! -d ~/.commcare-cloud ] && mkdir ~/.commcare-cloud
if [ ! -d ~/.commcare-cloud/repo ]
then
    ln -sf "${ANSIBLE_REPO}" ~/.commcare-cloud/repo
fi

if [ ! -f "${FAB_CONFIG}" ]
then
    for OLD_FAB_DIR in "${ANSIBLE_REPO}/../commcare-hq/deployment/commcare-hq-deploy" "${ANSIBLE_REPO}/../commcare-hq-deploy"
    do
        if [ -d "${OLD_FAB_DIR}" ]
        then
            OLD_FAB_CONFIG="${OLD_FAB_DIR}/fab/config.py"
            if [ -f "${OLD_FAB_CONFIG}" ]
            then
                cp "${OLD_FAB_CONFIG}" "${FAB_CONFIG}"
                break
            fi
        fi
    done
fi
