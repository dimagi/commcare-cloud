# Manual Installation

## Install and setup
You will need python 3.6 and `virtualenvwrapper` installed to follow these instructions:

```
sudo apt-get install git python-dev python-pip
sudo pip install virtualenv virtualenvwrapper --ignore-installed six
```

## Setup

Download and run the `control/init.sh` script. This should be run from your home directory:

```
source <(curl -s https://raw.githubusercontent.com/dimagi/commcare-cloud/master/control/init.sh)
```

You may now use `commcare-cloud` or its shorter alias `cchq` whenever you're in the virtualenv.

`~/init-ansible` may be used in future sessions to activate the virtualenv and
update requirements. If you want that to happen automatically when you create a
new interactive shell, add the following to your `~/.profile`:

```sh
[ -t 1 ] && source ~/init-ansible
```

## Manual setup

If you'd rather use your own virtualenv name, or the script above didn't work for you
the set up is pretty simple. Just run:

```
$ mkvirtualenv ansible
(ansible)$ git clone https://github.com/dimagi/commcare-cloud.git
(ansible)$ pip install pip-tools
(ansible)$ pip-sync commcare-cloud/requirements.txt
(ansible)$ pip install -e commcare-cloud/
(ansible)$ manage-commcare-cloud install
(ansible)$ manage-commcare-cloud configure  # and copy the line from here into your ~/.bash_profile
```

You will then be able to use cchq from anywhere.

## git-hook setup

If you have done the manual setup, Before making any commits, make sure you install the git hooks:
the set up is pretty simple. Just run:

```
(ansible)$ cd ~/commcare-cloud
(ansible)$ ./git-hooks/install.sh
```

This will make sure you never commit an unencrypted vault.yml file.
