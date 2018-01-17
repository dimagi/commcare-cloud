# Set up commcare-cloud

You will need python 2.7 and virtualenvwrapper installed. To follow these instructions.

Clone the commcare-cloud repo (suggested location alongside commcare-hq):

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
