#!/usr/bin/env bash

function realpath() {
    python -c "import os,sys; print os.path.realpath(sys.argv[1])" $1
}

ANSIBLE_REPO="$(realpath $(dirname $0)/..)"
FAB_CONFIG="${ANSIBLE_REPO}/fab/fab/config.py"

if [ ! -d ~/.commcare-cloud ]
then
    mkdir ~/.commcare-cloud
    echo "→ Created ~/.commcare-cloud"
else
    echo "✓ ~/.commcare-cloud exists"
fi
if [ ! -d ~/.commcare-cloud/repo ]
then
    ln -sf "${ANSIBLE_REPO}" ~/.commcare-cloud/repo
    echo "→ Linked this repo to ~/.commcare-cloud/repo"
else
    echo "✓ ~/.commcare-cloud/repo exists"
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
                echo "→ Copied ${OLD_FAB_CONFIG} to ${FAB_CONFIG}"
                break
            fi
        fi
    done
else
    echo "✓ ${FAB_CONFIG} exists"
fi
# fab config _still_ doesn't exist, note that we were unsuccessful in inferring it
if [ ! -f "${FAB_CONFIG}" ]
then
    echo "✗ ${FAB_CONFIG} does not exist and suitable location to copy it from was not found."
    echo "  This file is just a convenience, so this is a non-critical error."
    echo "  If you have fab/config.py in a previous location, then copy it to ${FAB_CONFIG}."
fi
