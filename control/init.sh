#! /bin/bash
if ! hash virtualenvwrapper.sh 2>/dev/null; then
    echo "Please install virtualenvwrapper and make sure it is in your PATH"
    echo ""
    echo "  sudo apt-get install git python-dev python-pip"
    echo "  sudo pip install virtualenv virtualenvwrapper"
    return 1
fi

source virtualenvwrapper.sh

if [ ! -d ~/.virtualenvs/ansible ]; then
    echo "Creating ansible virtualenv..."
    mkvirtualenv ansible
else
    workon ansible
fi

if [ -d ~/commcarehq-ansible ]; then
    echo "Moving repo to ~/commcare-cloud"
    mv ~/commcarehq-ansible ~/commcare-cloud
    # delete broken link
    [ ! -f ~/init-ansible ] && rm -f ~/init-ansible
fi

if [ ! -d ~/commcare-cloud ]; then
    echo "Checking out CommCare Cloud Repo"
    git clone https://github.com/dimagi/commcare-cloud.git
    # first time install need requiremnts installed in serial
    cd ~/commcare-cloud && pip install -r ~/commcare-cloud/requirements.txt && cd -
else
    cd ~/commcare-cloud && pip install -r ~/commcare-cloud/requirements.txt && cd - &
fi

echo "Downloading dependencies from galaxy and pip"
export ANSIBLE_ROLES_PATH=~/.ansible/roles
pip install pip --upgrade &
ansible-galaxy install -r ~/commcare-cloud/ansible/requirements.yml &
wait

# convenience: . init-ansible
[ ! -f ~/init-ansible ] && ln -s ~/commcare-cloud/control/init.sh ~/init-ansible
cd ~/commcare-cloud && ./control/check_install.sh && cd -
alias update-code='~/commcare-cloud/control/update_code.sh && . ~/init-ansible'
alias update_code='~/commcare-cloud/control/update_code.sh && . ~/init-ansible'

export PATH=$PATH:~/.commcare-cloud/bin
source ~/.commcare-cloud/repo/control/.bash_completion

YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if ! grep -q init-ansible ~/.profile; then
    printf "${YELLOW}Do you want to have the CommCare Cloud environment setup on login?${NC}"
    read -t 30 -p "(y/n): " yn
    case $yn in
        [Yy]* )
            echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile
            printf "${YELLOW}→ Added init script to ~/.profile"
        ;;
        * )
            printf "${BLUE}You can always set it up later by running this command:\n'
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
    printf "ap - Use ${YELLOW}commcare-cloud <env> ap{NC} instead.\n"
    printf "aps - Use ${YELLOW}commcare-cloud <env> aps${NC} instead.\n"
    printf "ae - Use ${YELLOW}commcare-cloud <env> run-shell-command${NC} instead.\n"
}

[ -t 1 ] && ansible-control-banner
cd ~/commcare-cloud
