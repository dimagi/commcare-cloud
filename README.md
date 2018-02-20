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
You will need python 2.7 and `virtualenvwrapper` installed
to follow these instructions.

Clone the commcare-cloud repo
(suggested location alongside commcare-hq, if you have that repo cloned as well):

```
git clone https://github.com/dimagi/commcare-cloud.git
cd commcare-cloud
```

Now make a virtualenv for ansible:

```
mkvirtualenv ansible
```

If you want `workon ansible` to always bring you to this directory, then you can also run

```
setvirtualenvproject
```

at this time.

**Note**: If you already have commcare-cloud cloned, then just enter that directory
and update it with

```
git pull
```

# Install commcare-cloud

You must be in your virtualenv for the install script to work
```
workon ansible
```

Then, simply run:

```
./install.sh
```

You may now use `commcare-cloud` or its shorter alias `cchq` whenever you're in the virtualenv.

# Optional: Hook up the bells and whistles

To be able to
- use `commcare-cloud` (and its alias `cchq`) from anywhere
- use `commcare-cloud` bash completion

add the following to your bash profile:

```
export PATH=$PATH:~/.commcare-cloud/bin
source ~/.commcare-cloud/repo/control/.bash_completion
```


# Contributing

Before making any commits, make sure you install the git hooks:

```
./git-hooks/install.sh
```

This will make sure you never commit an unencrypted vault.yml file.
