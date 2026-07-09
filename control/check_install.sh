#!/usr/bin/env bash

function realpath() {
    python -c "import os,sys; print(os.path.realpath(sys.argv[1]))" $1
}

COMMCARE_CLOUD_REPO="$(realpath $(dirname $0)/..)"
FAB_CONFIG="${COMMCARE_CLOUD_REPO}/src/commcare_cloud/config.py"
FAB_CONFIG_EXAMPLE="${COMMCARE_CLOUD_REPO}/src/commcare_cloud/config.example.py"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
