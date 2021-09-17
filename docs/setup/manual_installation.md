# Manual Installation

## Install and setup
You will need python 3.6 installed to follow these instructions (for
Ubuntu 18.04; other operating systems may differ):

```
sudo apt-get install git python3-dev python3-pip
```

## Setup

Download and run the `control/init.sh` script. This should be run from your home directory:

```
source <(curl -s https://raw.githubusercontent.com/dimagi/commcare-cloud/master/control/init.sh)
```
You will see the following prompt
```
Do you want to have the CommCare Cloud environment setup on login?
(y/n):
```
If you answer 'y' then a line will be added to your .profile that will automatically run `source ~/init-ansible`
when you log in, sets up the commcare-cloud environment.
Otherwise, you can choose to run `source ~/init-ansible` manually to setup the environment during future sessions.

You may now use `commcare-cloud` or its shorter alias `cchq` whenever you're in the virtualenv.

## Manual setup

If you'd rather use your own virtualenv name or a different commcare-cloud repo
location, or if the script above did not work.

```sh
## Create/activate Python 3.6 virtualenv (name and location may be customized)
$ python3.6 -m pip install --user --upgrade virtualenv
$ python3.6 -m virtualenv ~/.virtualenvs/cchq
$ source ~/.virtualenvs/cchq/bin/activate

## Install commcare-cloud
(cchq)$ git clone https://github.com/dimagi/commcare-cloud.git
(cchq)$ pip install --upgrade pip-tools
(cchq)$ pip-sync commcare-cloud/requirements.txt
(cchq)$ pip install -e commcare-cloud
(cchq)$ manage-commcare-cloud install

## Optional: to setup local environments and use commcare-cloud (cchq) without
## first activating virtualenv. Follow interactive prompts and instructions.
(cchq)$ manage-commcare-cloud configure
```

If you opted out of the final `manage-commcare-cloud configure` step and you
have a local environments directory or cloned the repo somewhere other than
`~/commcare-cloud` you should set one or both of the following in your bash
profile (`~/.profile`) as needed:

```sh
# for non-standard commcare-cloud repo location
export COMMCARE_CLOUD_REPO=/path/to/your/commcare-cloud

# for local environments (other than $COMMCARE_CLOUD_REPO/environments)
export COMMCARE_CLOUD_ENVIRONMENTS=/path/to/your/environments
```

## git-hook setup

If you have done the manual setup, Before making any commits, make sure you install the git hooks:
the set up is pretty simple. Just run:

```
(cchq)$ ~/commcare-cloud/git-hooks/install.sh
```

This will make sure you never commit an unencrypted vault.yml file.
