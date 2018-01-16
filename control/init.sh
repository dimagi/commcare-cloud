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

if [ ! -d ~/commcarehq-ansible/config ]; then
    git clone /home/ansible/commcarehq-ansible-secrets.git ~/commcarehq-ansible/config || mkdir ~/commcarehq-ansible/config
fi

echo "Downloading dependencies from galaxy and pip"
export ANSIBLE_ROLES_PATH=~/.ansible/roles
ansible-galaxy install -r ~/commcarehq-ansible/ansible/requirements.yml &
pip install -r ~/commcarehq-ansible/ansible/requirements.txt &
pip install -e ~/commcarehq-ansible/commcare-cloud &
pip install -r ~/commcarehq-ansible/fab/requirements.txt &
pip install pip --upgrade &
wait

# convenience: . init-ansible
[ ! -f ~/init-ansible ] && ln -s ~/commcarehq-ansible/control/init.sh ~/init-ansible
~/commcarehq-ansible/control/check_install.sh
alias update-code='~/commcarehq-ansible/control/update_code.sh && . ~/init-ansible'
alias update_code='~/commcarehq-ansible/control/update_code.sh && . ~/init-ansible'

export PATH=$PATH:~/.commcare-cloud/bin
source ~/.commcare-cloud/repo/control/.bash_completion

function ap() {
    ENV=$1
    shift
    commcare-cloud $ENV ansible-playbook $@
}


function aps() {
    ENV=$1
    shift
    ap $ENV deploy_stack.yml $@
}

function ae() {
    ansible $1 -m shell -a "$2" -u ansible -i ~/commcarehq-ansible/fab/fab/inventory/$ENV
}

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
    echo 'ENV='$env' && USER='`whoami` '&& ANSIBLE_DIR=/home/$USER/commcarehq-ansible/ansible && /home/$USER/.virtualenvs/ansible/bin/ansible-playbook -u root -i $ANSIBLE_DIR/inventories/localhost $ANSIBLE_DIR/deploy_control.yml -e @$ANSIBLE_DIR/vars/$ENV/${ENV}_vault.yml -e @$ANSIBLE_DIR/vars/$ENV/${ENV}_public.yml --diff --ask-vault-pass'
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
    printf "${BLUE}commcare-cloud${NC} - CLI wrapper for ansible. See ${YELLOW}commcare-cloud -h${NC} for more details.\n"
    printf "ap - Alias for ${YELLOW}commcare-cloud <env> ansible-playbook${NC} e.g. ap production deploy_proxy.yml \n"
    printf "aps - Alias for ${YELLOW}commcare-cloud <env> ansible-playbook deploy_stack.yml${NC} e.g. aps production \n"
    printf "${BLUE}ansible-deploy-control [environment]${NC} - deploy changes to users on this control machine\n"
    printf "${BLUE}ae${NC} - allows running ad hoc commands on specified machines e.g. ae riakcs 'grep OOM /var/log/riak/console.log'\n"
}

[ -t 1 ] && ansible-control-banner
cd ~/commcarehq-ansible
