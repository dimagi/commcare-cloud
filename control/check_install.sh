#!/usr/bin/env bash

function realpath() {
    python -c "import os,sys; print os.path.realpath(sys.argv[1])" $1
}

ANSIBLE_REPO="$(realpath $(dirname $0)/..)"
FAB_CONFIG="${ANSIBLE_REPO}/fab/fab/config.py"
ORIGIN=$(git remote get-url origin)
OLD_ORIGIN_HTTPS_RE="https://github.com/dimagi/commcarehq-ansible(.git)?"
OLD_ORIGIN_SSH_RE="git@github.com:dimagi/commcarehq-ansible(.git)?"
OLD_ORIGIN_HTTPS="https://github.com/dimagi/commcarehq-ansible.git"
OLD_ORIGIN_SSH="git@github.com:dimagi/commcarehq-ansible.git"
NEW_ORIGIN_HTTPS="https://github.com/dimagi/commcare-cloud.git"
NEW_ORIGIN_SSH="git@github.com:dimagi/commcare-cloud.git"
if [[ "${ORIGIN}" =~ ${OLD_ORIGIN_HTTPS_RE} ]]
then
    git remote set-url origin ${NEW_ORIGIN_HTTPS}
    echo "→ Set origin to ${NEW_ORIGIN_HTTPS}"
elif [[ "${ORIGIN}" =~ ${OLD_ORIGIN_SSH_RE} ]]
then
    git remote set-url origin ${NEW_ORIGIN_SSH}
    echo "→ Set origin to ${NEW_ORIGIN_SSH}"
elif [ "${ORIGIN}" = ${NEW_ORIGIN_HTTPS} -o "${ORIGIN}" = ${NEW_ORIGIN_SSH} ]
then
    echo "✓ origin already set to ${ORIGIN}"
else
    echo "✗ origin is not recognized: ${ORIGIN}"
fi

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

if [ ! -d ~/.commcare-cloud/bin ]
then
    mkdir ~/.commcare-cloud/bin
    echo "→ Created ~/.commcare-cloud/bin"
else
    echo "✓ ~/.commcare-cloud/bin exists"
fi

for executable in commcare-cloud cchq
do
    if [ ! -f ~/.commcare-cloud/bin/${executable} ]
    then
        if [ -h ~/.commcare-cloud/bin/${executable} ]
        then
            # if '! -f' (file does not exist) but '-h' (is symbolic link)
            # then that means it's a broken link
            rm ~/.commcare-cloud/bin/${executable}
        fi
        if [ -z "$(which ${executable})" ]
        then
            echo "✗ No executable found for ${executable}. Skipping"
        else
            ln -sf $(which ${executable}) ~/.commcare-cloud/bin/
            echo "→ Created ~/.commcare-cloud/bin/${executable}"
        fi
    else
        echo "✓ ~/.commcare-cloud/bin/${executable} exists"
    fi
done

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
                echo "→ Copied $(realpath ${OLD_FAB_CONFIG}) to ${FAB_CONFIG}"
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
