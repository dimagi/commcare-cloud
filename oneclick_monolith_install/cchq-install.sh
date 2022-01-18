# # Run as sudo cchq-install.sh

# #!/bin/sh
set -e

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
printf "\nStep 1: Installing Requirements \n"
sudo apt -qq update
sudo apt -qq install python3-pip sshpass
sudo -H pip3 -q install --upgrade pip
update-alternatives --install /usr/bin/python python /usr/bin/python3 10
pip -q install ansible virtualenv virtualenvwrapper --ignore-installed six

printf "\nStep 2: Installing commcare-cloud \n"
# install comcare-cloud
DIR="${BASH_SOURCE%/*}"
if [[ ! -d "$DIR" ]]; then DIR="$PWD"; fi
source "$DIR/../control/init.sh"
touch /var/log/ansible.log && chmod 666 /var/log/ansible.log


printf "\nStep 3: Initializing environments directory for storing your CommCareHQ instance's configuration \n"
ansible-playbook --connection=local --extra-vars "@$config_file_path" "$DIR/bootstrap-env-playbook.yml" 
printf "\n Encrypting your environment's passwords file using ansible-vault. Please store this password safely as it will be required latter \n"
ansible-vault encrypt ~/environments/$env_name/vault.yml

printf "\bStep 4: Setting up users and SSH auth \n"
source ~/.commcare-cloud/load_config.sh
commcare-cloud $env_name update-local-known-hosts
commcare-cloud $env_name bootstrap-users -c local
printf "\ncommcare-cloud setup is successful! You can now install CommCareHQ using below command\n"
printf "commcare-cloud $env_name deploy-stack --skip-check --skip-tags=users -e 'CCHQ_IS_FRESH_INSTALL=1' -c local \n"