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
    pip install -r ~/commcarehq-ansible/ansible/requirements.txt
else
    workon ansible
fi

if [ ! -d ~/commcarehq-ansible/config ]; then
    git clone /home/ansible/commcarehq-ansible-secrets.git ~/commcarehq-ansible/config
fi

if [ ! -d ~/commcare-hq-deploy ]; then
    echo "Cloning commcare-hq-deploy..."
    git clone git@github.com:dimagi/commcare-hq-deploy ~/commcare-hq-deploy
    if [ ! -d ~/commcare-hq ]; then
        # keep old commands working: create symlink to simulate cchq repo
        mkdir ~/commcare-hq
        ln -s ~/commcare-hq-deploy/fab ~/commcare-hq/fab
    fi
fi

# convenience: . init-ansible
[ ! -f ~/init-ansible ] && ln -s ~/commcarehq-ansible/control/init.sh ~/init-ansible

alias ap='ansible-playbook -u ansible -i ../../commcare-hq-deploy/fab/inventory/$ENV -e "@../config/$ENV/$ENV.yml" --ask-sudo-pass'
alias aps='ap deploy_stack.yml'
alias update-code='~/commcarehq-ansible/control/update_code.sh'
alias update_code='~/commcarehq-ansible/control/update_code.sh'

function ansible-deploy-control() {
  ANSIBLE_CONTROL_USER=`whoami` && sudo /home/$ANSIBLE_CONTROL_USER/.virtualenvs/ansible/bin/ansible-playbook -u root -i inventories/localhost deploy_control.yml -e @../config/$ENV/$ENV.yml --diff
}

function ansible-control-banner() {
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
    printf "\n${GREEN}Welcome to Ansible Control\n\n"
    printf "${GREEN}Available commands:\n"
    printf "${BLUE}update-code${NC} - update the ansible repositories (safely)\n"
    printf "${BLUE}workon ansible${NC} - activate the ansible virtual env\n"
    printf "${BLUE}ap${NC} - shortcut for ansible-playbook -u ansible -i ../../commcare-hq/fab/inventory/\$ENV -e \"@../config/\$ENV/\$ENV.yml\" --ask-sudo-pass\n"
    printf "${BLUE}aps${NC} - same as ap deploy_stack.yml\n"
    printf "${BLUE}ansible-deploy-control${NC} - deploy changes to users on this control machine\n"
}

[ -t 1 ] && ansible-control-banner
cd ~/commcarehq-ansible/ansible
