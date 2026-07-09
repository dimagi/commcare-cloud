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

if [ ! -f "${FAB_CONFIG}" ]; then
    cp "${FAB_CONFIG_EXAMPLE}" "${FAB_CONFIG}"
    printf "${YELLOW}→ Copied $(realpath ${FAB_CONFIG_EXAMPLE}) to ${FAB_CONFIG}\n"
else
    printf "${GREEN}✓ ${FAB_CONFIG} exists\n"
fi

printf "${NC}"
