#!/usr/bin/env bash

function realpath() {
    python -c "import os,sys; print os.path.realpath(sys.argv[1])" $1
}

function git_remote_get_url() {
    # git 1.9-compatible replacement for `git remote get-url <remote>`
    git remote show ${1} | head -n2 | tail -n1 | grep -o '[^ ]*$'
}
ANSIBLE_REPO="$(realpath $(dirname $0)/..)"
FAB_CONFIG="${ANSIBLE_REPO}/fab/fab/config.py"
ORIGIN=$(git_remote_get_url origin)
OLD_ORIGIN_HTTPS_RE="https://github.com/dimagi/commcarehq-ansible(.git)?"
OLD_ORIGIN_SSH_RE="git@github.com:dimagi/commcarehq-ansible(.git)?"
OLD_ORIGIN_HTTPS="https://github.com/dimagi/commcarehq-ansible.git"
OLD_ORIGIN_SSH="git@github.com:dimagi/commcarehq-ansible.git"
NEW_ORIGIN_HTTPS="https://github.com/dimagi/commcare-cloud.git"
NEW_ORIGIN_SSH="git@github.com:dimagi/commcare-cloud.git"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [[ "${ORIGIN}" =~ ${OLD_ORIGIN_HTTPS_RE} ]]
then
    git remote set-url origin ${NEW_ORIGIN_HTTPS}
    printf "${YELLOW}→ Set origin to ${NEW_ORIGIN_HTTPS}\n"
elif [[ "${ORIGIN}" =~ ${OLD_ORIGIN_SSH_RE} ]]
then
    git remote set-url origin ${NEW_ORIGIN_SSH}
    printf "${YELLOW}→ Set origin to ${NEW_ORIGIN_SSH}\n"
elif [ "${ORIGIN}" = ${NEW_ORIGIN_HTTPS} -o "${ORIGIN}" = ${NEW_ORIGIN_SSH} ]
then
    printf "${GREEN}✓ origin already set to ${ORIGIN}\n"
else
    printf "${RED} origin is not recognized: ${ORIGIN}\n"
fi

if [ ! -d ~/.commcare-cloud ]
then
    mkdir ~/.commcare-cloud
    printf "${YELLOW}→ Created ~/.commcare-cloud\n"
else
    printf "${GREEN}✓ ~/.commcare-cloud exists\n"
fi

if [ ! -d ~/.commcare-cloud/repo ]
then
    ln -sf "${ANSIBLE_REPO}" ~/.commcare-cloud/repo
    printf "${YELLOW}→ Linked this repo to ~/.commcare-cloud/repo\n"
else
    printf "${GREEN}✓ ~/.commcare-cloud/repo exists\n"
fi

if [ ! -d ~/.commcare-cloud/bin ]
then
    mkdir ~/.commcare-cloud/bin
    printf "${YELLOW}→ Created ~/.commcare-cloud/bin\n"
else
    printf "${GREEN}✓ ~/.commcare-cloud/bin exists\n"
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
            printf "${RED}✗ No executable found for ${executable}. Skipping\n"
        else
            ln -sf $(which ${executable}) ~/.commcare-cloud/bin/
            printf "${YELLOW}→ Created ~/.commcare-cloud/bin/${executable}\n"
        fi
    else
        printf "${GREEN}✓ ~/.commcare-cloud/bin/${executable} exists\n"
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
                printf "${YELLOW}→ Copied $(realpath ${OLD_FAB_CONFIG}) to ${FAB_CONFIG}\n"
                break
            fi
        fi
    done
else
    printf "${GREEN}✓ ${FAB_CONFIG} exists\n"
fi
# fab config _still_ doesn't exist, note that we were unsuccessful in inferring it
if [ ! -f "${FAB_CONFIG}" ]
then
    printf "${RED}✗ ${FAB_CONFIG} does not exist and suitable location to copy it from was not found.\n"
    printf "${BLUE}  This file is just a convenience, so this is a non-critical error.\n"
    printf "${BLUE}  If you have fab/config.py in a previous location, then copy it to ${FAB_CONFIG}.${NC}\n"
fi
