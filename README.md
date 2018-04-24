# CommCare-Cloud

[![Build
Status](https://travis-ci.org/dimagi/commcare-cloud.svg?branch=master)](https://travis-ci.org/dimagi/commcare-cloud)

Tools for standing up and managing a CommCare HQ server environment.

Docs at [https://dimagi.github.io/commcare-cloud/](https://dimagi.github.io/commcare-cloud/)
.

# Components

- Ansible
- Fabric
- configurable environments (under `environments/`)
- Assorted small tools for managing and accessing servers
- Command line interface (`commcare-cloud`) for running commands backed
  by the other components


# Install and setup
You will need python 2.7.12+ and `virtualenvwrapper` installed to follow these instructions:

```
sudo apt-get install git python-dev python-pip
sudo pip install virtualenv virtualenvwrapper --ignore-installed six
```

# Setup

This should be run from your home directory:
```
source <(curl -s https://raw.githubusercontent.com/dimagi/commcare-cloud/master/control/init.sh)
```

Alternatively:

```
git clone https://github.com/dimagi/commcare-cloud.git
source commcare-cloud/control/init.sh
```

You may now use `commcare-cloud` or its shorter alias `cchq` whenever you're in the virtualenv.

We also recommend that you put the following in your `~/.profile` which gives you access to the tool
from anywhere:
```
export PATH=$PATH:~/.commcare-cloud/bin
source ~/.commcare-cloud/repo/control/.bash_completion
```

# Manual setup

If you'd rather use your own virtualenv name, or the script above didn't work for you
the set up is pretty simple. Just run:

```
$ mkvirtualenv ansible
(ansible)$ git clone https://github.com/dimagi/commcare-cloud.git
(ansible)$ pip install -e commcare-cloud/
(ansible)$ manage-commcare-cloud install
(ansible)$ manage-commcare-cloud configure  # and copy the line from here into your ~/.bash_profile
```

You will then be able to use cchq from anywhere.


# Contributing

Before making any commits, make sure you install the git hooks:

```
./git-hooks/install.sh
```

This will make sure you never commit an unencrypted vault.yml file.


# Running tests

To run tests, first install the test dependencies

```
pip install -e .[test]
```

and then run

```
nosetests
```

Tests include tests of your own specific environments dir.
