# Set up commcarehq-ansible

Clone the commcarehq-ansible repo (suggested location alongside commcare-hq):

```
git clone https://github.com/dimagi/commcarehq-ansible.git
cd commcarehq-ansible
```

Now make a virtualenv for ansible:

```
mkvirtualenv ansible
```

**Note**: If you already have commcarehq-ansible cloned, then just enter that directory
and update it with

```
git pull
```

# Install commcare-cloud

```
workon ansible
```

```
pip install pip --upgrade
```

```
pip install -e commcare-cloud
pip install -r ansible/requirements.txt  # to be able to run ansible commands
ansible-galaxy install -r ansible/requirements.yml  # to be able to run ansible commands
pip install -r fab/requirements.txt  # to be able to run fab commands
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

source ~/.commcare-cloud/repo/control/.bash_completion

to your bash profile.

`commcare-cloud` also comes with an alias to the same command, `cchq`. You may link this
to somewhere on your path as well. All together that comes to something like

```
ln -sf ~/.virtualenvs/ansible/bin/commcare-cloud /usr/local/bin
ln -sf ~/.virtualenvs/ansible/bin/cchq /usr/local/bin
source ~/.commcare-cloud/repo/control/.bash_completion
```

though you may have to modify that somewhat for your own environment.
