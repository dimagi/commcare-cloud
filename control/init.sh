#! /bin/bash
NO_INPUT=${NO_INPUT:-0}

if [[ $_ == $0 ]]
then
    echo "Please run this script as follows:"
    echo "    $ source /path/to/repo/control/init.sh"
    exit 1
fi

if ! command -v uv > /dev/null; then
    echo "uv is required. See https://docs.astral.sh/uv/getting-started/installation/"
    printf "For example:\n    sudo snap install astral-uv --classic\n\n"
    # snap does a system-wide install with automatic updates
    return 1
fi

function realpath() {
    python -c "import os,sys; print(os.path.realpath(sys.argv[1]))" $1
}

if [ -n "${BASH_SOURCE[0]}" ] && [ -z "${BASH_SOURCE[0]##*init.sh*}" ]
then
    # this script is being run from a file on disk, presumably from within commcare-cloud repo
    COMMCARE_CLOUD_REPO=$(dirname $(dirname $(realpath ${BASH_SOURCE[0]})))

    # check for expected file to verify we've got the right place
    if [ ! -f ${COMMCARE_CLOUD_REPO}/control/update_code.sh ]
    then
        echo "It looks like you're running this script from an unexpected location."
        echo "Please check the README for installation instructions:"
        echo "    https://github.com/dimagi/commcare-cloud/blob/master/README.md"
        return 1
    fi
else
    # use pre-assigned location if set; fallback to the default location
    COMMCARE_CLOUD_REPO=${COMMCARE_CLOUD_REPO:-${HOME}/commcare-cloud}
fi

if [ ! -d ${COMMCARE_CLOUD_REPO} ]; then
    # Used by docs/source/reference/1-commcare-cloud/1-installation.rst
    # Manual Installation: source <(curl -s https://.../control/init.sh)
    echo "Checking out CommCare Cloud Repo"
    git clone https://github.com/dimagi/commcare-cloud.git $COMMCARE_CLOUD_REPO
fi

cd ${COMMCARE_CLOUD_REPO}
uv sync
uv run --no-sync manage-commcare-cloud install

# Put the project venv on PATH so `cchq`, `commcare-cloud`, `ansible-playbook` etc.
# are directly invokable without `uv run`.
if [ -n "${UV_PROJECT_ENVIRONMENT}" ] && [ -d "${UV_PROJECT_ENVIRONMENT}/bin" ]; then
    export PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
elif [ -d "${COMMCARE_CLOUD_REPO}/.venv/bin" ]; then
    export PATH="${COMMCARE_CLOUD_REPO}/.venv/bin:${PATH}"
fi

# git-hook install to protect the commit of unencrypted vault.yml file
if [ ! -f "${COMMCARE_CLOUD_REPO}/.git/hooks/pre-commit" ]
then
    echo " Installing git-hook precommit to protect the commit of unprotected vault.yml file"
    ./git-hooks/install.sh && echo "Installed git-hook precommit" || echo "Failed to Install git-hook precommit, Install manually ./git-hooks/install.sh"
fi

# convenience: . init-ansible
[ ! -f ~/init-ansible ] && ln -s ${COMMCARE_CLOUD_REPO}/control/init.sh ~/init-ansible
./control/check_install.sh
alias update-code='${COMMCARE_CLOUD_REPO}/control/update_code.sh && (cd ${COMMCARE_CLOUD_REPO} && uv sync --quiet)'
alias update_code=update-code

source ${COMMCARE_CLOUD_REPO}/src/commcare_cloud/.bash_completion

YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [ -z ${CI_TEST} ]; then
  if ! grep -q init-ansible ~/.profile 2>/dev/null; then
    if [ $NO_INPUT == 1 ]; then
      yn='y'
    else
      printf "${YELLOW}Do you want to have the CommCare Cloud environment setup on login?${NC}\n"
      read -t 30 -p "(y/n): " yn
    fi
    case $yn in
        [Yy]* )
            echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile
            printf "${YELLOW}→ Added init script to ~/.profile\n"
        ;;
        [Nn]* )
            echo '# [ -t 1 ] && source ~/init-ansible' >> ~/.profile
            printf "${YELLOW}→ Okay, I won't ask you again. Added a line you can uncomment in ~/.profile if you want it later.\n"
        ;;
        * )
            printf "\n${BLUE}You can always set it up later by running this command:\n"
            printf "${BLUE}echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile${NC}\n"
        ;;
    esac
  fi
fi

function ansible-control-banner() {
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[0;33m'
    NC='\033[0m' # No Color
    printf "\n${GREEN}Welcome to commcare-cloud\n\n"
    printf "${GREEN}Available commands:\n"
    printf "${BLUE}update-code${NC} - update the commcare-cloud repositories (safely)\n"
    printf "${BLUE}commcare-cloud${NC} - CLI wrapper for ansible.\n"
    printf "                 See ${YELLOW}commcare-cloud -h${NC} for more details.\n"
    printf "                 See ${YELLOW}commcare-cloud <env> <command> -h${NC} for command details.\n"
}

[ -t 1 ] && ansible-control-banner
cd ${COMMCARE_CLOUD_REPO}
