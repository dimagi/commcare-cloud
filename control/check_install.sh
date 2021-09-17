#!/usr/bin/env bash

function realpath() {
    python -c "import os,sys; print(os.path.realpath(sys.argv[1]))" $1
}

function git_remote_get_url() {
    # git 1.9-compatible replacement for `git remote get-url <remote>`
    git remote show ${1} | head -n2 | tail -n1 | grep -o '[^ ]*$'
}
COMMCARE_CLOUD_REPO="$(realpath $(dirname $0)/..)"
FAB_CONFIG="${COMMCARE_CLOUD_REPO}/src/commcare_cloud/config.py"
FAB_CONFIG_EXAMPLE="${COMMCARE_CLOUD_REPO}/src/commcare_cloud/config.example.py"
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

# clean up obsolete ~/.commcare-cloud stuff
[ -d ~/.commcare-cloud/bin ] && { rm ~/.commcare-cloud/bin/*; rmdir ~/.commcare-cloud/bin; }
[ -h ~/.commcare-cloud/repo ] && rm ~/.commcare-cloud/repo

if [ ! -f "${FAB_CONFIG}" ]
then
    OLD_FAB_CONFIG="${COMMCARE_CLOUD_REPO}/src/commcare_cloud/fab/config.py"
    if [ -f "${OLD_FAB_CONFIG}" ]
    then
        cp "${OLD_FAB_CONFIG}" "${FAB_CONFIG}"
        printf "${YELLOW}→ Copied $(realpath ${OLD_FAB_CONFIG}) to ${FAB_CONFIG}\n"
    fi
else
    printf "${GREEN}✓ ${FAB_CONFIG} exists\n"
fi
# fab config _still_ doesn't exist, note that we were unsuccessful in inferring it
if [ ! -f "${FAB_CONFIG}" ]
then
    cp "${FAB_CONFIG_EXAMPLE}" "${FAB_CONFIG}"
    printf "${YELLOW}→ Copied $(realpath ${FAB_CONFIG_EXAMPLE}) to ${FAB_CONFIG}\n"
fi

printf "${NC}"
