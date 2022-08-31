# # Run as bash cchq-install.sh install-config.yml

# #!/bin/sh
set -e

printf "Please note that you may be prompted for sudo permission for some of the commands.\n"

function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

get_abs_filename() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}
config_file_path=$(get_abs_filename $1)
# Load config vars
eval $(parse_yaml $config_file_path)

# update and install requirements
printf "\n"
printf "#################################################"
printf "\nStep 1: Installing Requirements \n"
printf "#################################################"
printf "\n"
sudo apt --assume-yes -qq update
sudo apt --assume-yes -qq install python3-pip sshpass
sudo -H pip3 -q install --upgrade pip
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 10
if [[ $CCHQ_VIRTUALENV == *3.10* ]]; then
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt update
  sudo apt-get --assume-yes -q install python3.10 python3.10-dev python3.10-distutils python3.10-venv libffi-dev
else
  sudo -H pip -q install ansible virtualenv --ignore-installed six
fi

printf "\n"
printf "#################################################"
printf "\nStep 2: Installing commcare-cloud \n"
printf "#################################################"
printf "\n"
# install comcare-cloud
DIR="${BASH_SOURCE%/*}"
if [[ ! -d "$DIR" ]]; then DIR="$PWD"; fi
echo y | source "$DIR/../control/init.sh"
sudo touch /var/log/ansible.log && sudo chmod 666 /var/log/ansible.log

printf "\n"
printf "#################################################"
printf "\nStep 3: Initializing environments directory for "
printf "storing your CommCareHQ instance's configuration \n"
printf "#################################################"
printf "\n"
# VENV should have been set by init.sh
DEFAULT_VENV=~/.virtualenvs/cchq
VENV=${VENV:-$DEFAULT_VENV}

ansible-playbook --connection=local --extra-vars "@$config_file_path" --extra-vars "cchq_venv=$VENV" "$DIR/bootstrap-env-playbook.yml"
printf "\n Encrypting your environment's passwords file using ansible-vault.\n"
printf "Please store this password safely as it will be asked multiple times during the install.\n"
ansible-vault encrypt ~/environments/$env_name/vault.yml

printf "\n"
printf "#################################################"
printf "\nStep 4: Setting up users and SSH auth \n"
printf "#################################################"
printf "\n"
source ~/.commcare-cloud/load_config.sh
commcare-cloud $env_name update-local-known-hosts
commcare-cloud $env_name bootstrap-users -c local --quiet

printf "\nEverything is setup to install CommCareHQ now! Would you like to install CommCareHQ now?\n"
printf "Please see below a summary of what this script has setup so far!\n"
printf "1. Installed commcare-cloud, the tool to deploy and manage your CommCareHQ instance.\n"
printf "2. Users ansible and $ssh_username are created with SSH and sudo access.\n"
printf "3. A configuration directory created for your CommCareHQ environment at: $HOME/environments/$env_name.\n"
printf "  This directory has all the configuration and the encrypted vault file containing passwords.\n"
printf "  The vault file also has the sudo password for the ansible user under the key ansible_sudo_pass\n\n"

printf "You can now install CommCareHQ using below two commands.\n\n"
printf "source ~/.commcare-cloud/load_config.sh\n"
printf "commcare-cloud $env_name deploy-stack --skip-check --skip-tags=users -e 'CCHQ_IS_FRESH_INSTALL=1' -c local \n\n"
printf "Would you like the above command to be run now?\n"
read -p "(Please note that if this command fails midway, you can run this command directly instead of rerunning the cchq-install command) Proceed (Y/n)?" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    commcare-cloud $env_name deploy-stack --skip-check --skip-tags=users -e 'CCHQ_IS_FRESH_INSTALL=1' -c local --quiet
else
    exit
fi

printf "\nSuccessfully installed all the required services for CommCareHQ instance!\n"
printf "Prepareing the system for first time application (code) deploy\n"
commcare-cloud $env_name django-manage create_kafka_topics
commcare-cloud $env_name django-manage preindex_everything
printf "\nDeploying latest CommCareHQ Application code\n"
printf "If this fails you can run 'commcare-cloud $env_name deploy --resume' to try again"
commcare-cloud $env_name deploy
