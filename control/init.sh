#! /bin/bash

if [[ $_ == $0 ]]
then
    echo "Please run this script as follows:"
    echo "    $ source /path/to/repo/control/init.sh"
    exit 1
fi


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

    # check for expected file to verify we've got the right place
    if [ ! -f ${COMMCARE_CLOUD_REPO}/control/update_code.sh ]
    then
        echo "It looks like you're running this script from an unexpected location."
        echo "Please check the README for installation instructions:"
        echo "    https://github.com/dimagi/commcare-cloud/blob/master/README.md"
        return 1
    fi
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
        mkvirtualenv ansible --python $(which python2)
    elif ~/.virtualenvs/ansible/bin/python -c 'print ""' 2> /dev/null; [ "$?" -ne "0" ]; then
        echo "######################################################"
        echo "#                                                    #"
        echo "#  You're working from a python3 virtualenv,         #"
        echo "#  but commcare-cloud doesn't yet support Python 3.  #"
        echo "#  To reset your virtualenv, run the following:      #"
        echo "#                                                    #"
        echo "#    rmvirtualenv ansible                            #"
        echo "#                                                    #"
        echo "#  Then run this script again. If it runs on login,  #"
        echo "#  you can just log out and log back in.             #"
        echo "#                                                    #"
        echo "######################################################"
        return -1
    else
        workon ansible
    fi
fi

if [ -d ~/commcarehq-ansible ]; then
    echo "Moving repo to ~/commcare-cloud"
    mv ~/commcarehq-ansible ~/commcare-cloud
    # delete broken link
fi

# remove broken links
[ ! -f ~/init-ansible ] && rm -f ~/init-ansible

if [ ! -d ${COMMCARE_CLOUD_REPO} ]; then
    echo "Checking out CommCare Cloud Repo"
    git clone https://github.com/dimagi/commcare-cloud.git
fi

if [ -d ${COMMCARE_CLOUD_REPO}/commcare-cloud ]; then
    # we are on an old version of commcare-cloud before it was moved to src/
    rm -rf ${COMMCARE_CLOUD_REPO}/commcare-cloud
fi

if [ -z "$(which manage-commcare-cloud)" ]; then
    # first time install need requirements installed in serial
    # installs strictly what's in requirements.txt, so versions are pre-pinned
    cd ${COMMCARE_CLOUD_REPO} && pip install pip-tools && pip-sync && pip install -e . && cd -
else
    { COMMCARE= && cd ${COMMCARE_CLOUD_REPO} && pip install pip-tools && pip-sync && pip install -e . && cd - ; } &
fi

echo "Downloading dependencies from galaxy and pip"
export ANSIBLE_ROLES_PATH=~/.ansible/roles
COMMCARE= pip install pip --upgrade &
COMMCARE= manage-commcare-cloud install & # includes ansible-galaxy install

# wait for all processes that _we_ started
for pid in `jobs | grep 'COMMCARE=' | cut -d'[' -f2 | cut -d']' -f1`
do
    wait %${pid}
done

# workaround for some envs that got in a bad state
python -c 'import Crypto' || {
    echo "^--- Looks like there's an issue with the pycryptodome install,"
    echo "     but don't worry, we'll fix that for you."
    cd ${COMMCARE_CLOUD_REPO} && pip uninstall pycryptodome pycrypto --yes &&  pip-sync && pip install -e . && cd - ;
}

# convenience: . init-ansible
[ ! -f ~/init-ansible ] && ln -s ${COMMCARE_CLOUD_REPO}/control/init.sh ~/init-ansible
cd ${COMMCARE_CLOUD_REPO} && ./control/check_install.sh && cd -
alias update-code='${COMMCARE_CLOUD_REPO}/control/update_code.sh && . ~/init-ansible'
alias update_code='${COMMCARE_CLOUD_REPO}/control/update_code.sh && . ~/init-ansible'

export PATH=$PATH:~/.commcare-cloud/bin
source ~/.commcare-cloud/repo/src/commcare_cloud/.bash_completion

YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if ! grep -q init-ansible ~/.profile 2>/dev/null; then
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
            printf "${BLUE}echo '[ -t 1 ] && source ~/init-ansible' >> ~/.profile${NC}\n"
        ;;
    esac
fi

# It aint pretty, but it gets the job done
function ansible-deploy-control() {
    if [ -z "$1" ]; then
        echo "Usage:"
        echo "  ansible-deploy-control [environment]"
        return
    fi
    env="$1"
    echo "You must be root to deploy the control machine"
    echo "Run \`su\` to become the root user, then paste in this command to deploy:"
    echo 'ENV='$env' \
    && USER='`whoami`' \
    && ANSIBLE_DIR=/home/$USER/commcare-cloud/src/commcare_cloud/ansible \
    && ANSIBLE_CONFIG=$ANSIBLE_DIR/ansible.cfg \
    && ENV_DIR=/home/$USER/commcare-cloud/environments \
    && VENV=/home/$USER/.virtualenvs/ansible \
    && ANSIBLE_ROLES_PATH=$VENV/lib/python2.7/site-packages/.ansible/roles \
    $VENV/bin/ansible-playbook \
    -i localhost, $ANSIBLE_DIR/deploy_control.yml \
    -e @$ENV_DIR/$ENV/vault.yml \
    -e @$ENV_DIR/$ENV/public.yml \
    -e @$ENV_DIR/$ENV/.generated.yml \
    -e target=localhost --connection=local --diff --ask-vault-pass'
}

function ansible-control-banner() {
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[0;33m'
    NC='\033[0m' # No Color
    printf "\n${GREEN}Welcome to commcare-cloud\n\n"
    printf "${GREEN}Available commands:\n"
    printf "${BLUE}update-code${NC} - update the commcare-cloud repositories (safely)\n"
    printf "${BLUE}workon ansible${NC} - activate the ansible virtual environment\n"
    printf "${BLUE}ansible-deploy-control [environment]${NC} - deploy changes to users on this control machine\n"
    printf "${BLUE}commcare-cloud${NC} - CLI wrapper for ansible.\n"
    printf "                 See ${YELLOW}commcare-cloud -h${NC} for more details.\n"
    printf "                 See ${YELLOW}commcare-cloud <env> <command> -h${NC} for command details.\n"
}

[ -t 1 ] && ansible-control-banner
cd ${COMMCARE_CLOUD_REPO}
