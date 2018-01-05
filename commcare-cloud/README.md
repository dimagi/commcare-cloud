# Set up commcarehq-ansible

You will need python 2.7 and virtualenvwrapper installed. To follow these instructions.

Clone the commcarehq-ansible repo (suggested location alongside commcare-hq):

```
git clone https://github.com/dimagi/commcarehq-ansible.git
cd commcarehq-ansible
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

**Note**: If you already have commcarehq-ansible cloned, then just enter that directory
and update it with

```
git pull
```

# Install commcare-cloud

You need to be in the ansible virtualenv:
```
workon ansible
```
Additionally, you'll need the latest pip in your virtualenv for the following installs to work:
```
pip install pip --upgrade
```

Install the python requirements into your virtualenv:
```
pip install -r requirements.txt
```

To run ansible commands you will also need in install the galaxy modules:
```
ansible-galaxy install -r ansible/requirements.yml  # to be able to run ansible commands
```

Finally, finish your install with

```
./control/check_install.sh
```

# Optional: Hook up the bells and whistles

If you want to have access to the `commcare-cloud` command outside your virtualenv,
you can link the executable (within your vitualenv) to somewhere on your PATH.
While it's technically redundant, I like to accomplish this by adding the link command
to my bash profile:

```
ln -sf ~/.virtualenvs/ansible/bin/commcare-cloud /usr/local/bin
```

(Instead of `/usr/local/bin`, you will need to use a directory that is owned by your user
and on your PATH.)

If you want to have access to bash completion for the commcare-cloud command, you will
need to add

```
source ~/.commcare-cloud/repo/control/.bash_completion
```

to your bash profile.

`commcare-cloud` also comes with an alias to the same command, `cchq`. You may link this
to somewhere on your path as well. All together that comes to something like

```
ln -sf ~/.virtualenvs/ansible/bin/commcare-cloud /usr/local/bin
ln -sf ~/.virtualenvs/ansible/bin/cchq /usr/local/bin
source ~/.commcare-cloud/repo/control/.bash_completion
```

though you may have to modify that somewhat for your own environment.
