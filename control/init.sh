#! /bin/bash

function realpath() {
    python -c "import os,sys; print os.path.realpath(sys.argv[1])" $1
}


if [ -z ${TRAVIS_TEST} ]; then
    if ! hash virtualenvwrapper.sh 2>/dev/null; then
        echo "Please install virtualenvwrapper and make sure it is in your PATH"
        echo ""
        echo "  sudo pip install virtualenv virtualenvwrapper --ignore-installed six"
        echo ""
        echo "Other requirements: git, python-dev, python-pip"
        return 1
    fi
fi

if [ -n "${BASH_SOURCE[0]}" ] && [ -z "${BASH_SOURCE[0]##*init.sh*}" ]
then
    # this script is being run from a file on disk, presumably from within commcare-cloud repo
    COMMCARE_CLOUD_REPO=$(dirname $(dirname $(realpath ${BASH_SOURCE[0]})))
elif [ -d ~/.commcare-cloud/repo ]
then
    # commcare-cloud is already installed; use the one specified
    COMMCARE_CLOUD_REPO=~/.commcare-cloud/repo
else
    # commcare-cloud is not yet installed; use the default location
    COMMCARE_CLOUD_REPO=${HOME}/commcare-cloud
fi

if [ -z ${TRAVIS_TEST} ]; then
    source virtualenvwrapper.sh
    if [ ! -d ~/.virtualenvs/ansible ]; then
        echo "Creating ansible virtualenv..."
        mkvirtualenv ansible
    else
        workon ansible
    fi
fi

if [ -d ~/commcarehq-ansible ]; then
    echo "Moving repo to ~/commcare-cloud"
    mv ~/commcarehq-ansible ~/commcare-cloud
    # delete broken link
    [ ! -f ~/init-ansible ] && rm -f ~/init-ansible
fi

if [ ! -d ${COMMCARE_CLOUD_REPO} ]; then
    echo "Checking out CommCare Cloud Repo"
    git clone https://github.com/dimagi/commcare-cloud.git
fi

if [ -z "$(which ansible-galaxy)" ]; then
    # first time install need requirements installed in serial
    cd ${COMMCARE_CLOUD_REPO} && pip install -r ${COMMCARE_CLOUD_REPO}/requirements.txt && cd -
else
    cd ${COMMCARE_CLOUD_REPO} && pip install -r ${COMMCARE_CLOUD_REPO}/requirements.txt && cd - &
fi

echo "Downloading dependencies from galaxy and pip"
export ANSIBLE_ROLES_PATH=~/.ansible/roles
pip install pip --upgrade &
ansible-galaxy install -r ${COMMCARE_CLOUD_REPO}/ansible/requirements.yml &
wait

# convenience: . init-ansible
[ ! -f ~/init-ansible ] && ln -s ${COMMCARE_CLOUD_REPO}/control/init.sh ~/init-ansible
cd ${COMMCARE_CLOUD_REPO} && ./control/check_install.sh && cd -
alias update-code='${COMMCARE_CLOUD_REPO}/control/update_code.sh && . ~/init-ansible'
alias update_code='${COMMCARE_CLOUD_REPO}/control/update_code.sh && . ~/init-ansible'

export PATH=$PATH:~/.commcare-cloud/bin
source ~/.commcare-cloud/repo/control/.bash_completion

YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if ! grep -q init-ansible ~/.profile; then
    printf "${YELLOW}Do you want to have the CommCare Cloud environment setup on login?${NC}\n"
    if [ -z ${TRAVIS_TEST} ]; then
        read -t 30 -p "(y/n): " yn
    fi
    case $yn in
        [Yy]* )
            echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile
            printf "${YELLOW}→ Added init script to ~/.profile\n"
        ;;
        * )
            printf "\n${BLUE}You can always set it up later by running this command:\n"
            printf "${BLUE}'[ -t 1 ] && source ~/init-ansible' >> ~/.profile${NC}\n"
        ;;
    esac
fi

# It aint pretty, but it gets the job done
function ansible-deploy-control() {
    if [ -z "$1" ]; then
        echo "Usage:"
        echo "  ansible-deploy-control [environment]"
        exit 1
    fi
    env="$1"
    echo "You must be root to deploy the control machine"
    echo "Run \`su\` to become the root user, then paste in this command to deploy:"
    echo 'ENV='$env' && USER='`whoami` '&& ANSIBLE_DIR=/home/$USER/commcare-cloud/ansible && /home/$USER/.virtualenvs/ansible/bin/ansible-playbook -u root -i $ANSIBLE_DIR/inventories/localhost $ANSIBLE_DIR/deploy_control.yml -e @$ANSIBLE_DIR/vars/$ENV/${ENV}_vault.yml -e @$ANSIBLE_DIR/vars/$ENV/${ENV}_public.yml --diff --ask-vault-pass'
}

function ansible-control-banner() {
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[0;33m'
    NC='\033[0m' # No Color
    printf "\n${GREEN}Welcome to Ansible Control\n\n"
    printf "${GREEN}Available commands:\n"
    printf "${BLUE}update-code${NC} - update the ansible repositories (safely)\n"
    printf "${BLUE}workon ansible${NC} - activate the ansible virtual env\n"
    printf "${BLUE}ansible-deploy-control [environment]${NC} - deploy changes to users on this control machine\n"
    printf "${BLUE}commcare-cloud${NC} - CLI wrapper for ansible.\n"
    printf "                 See ${YELLOW}commcare-cloud -h${NC} for more details.\n"
    printf "                 See ${YELLOW}commcare-cloud <env> <command> -h${NC} for command details.\n"
    printf -- "\n${GREEN}Deprecated Commands${NC}\n"
    printf "ap - Use ${YELLOW}commcare-cloud <env> ap${NC} instead.\n"
    printf "aps - Use ${YELLOW}commcare-cloud <env> aps${NC} instead.\n"
    printf "ae - Use ${YELLOW}commcare-cloud <env> run-shell-command${NC} instead.\n"
}

[ -t 1 ] && ansible-control-banner
cd ${COMMCARE_CLOUD_REPO}
