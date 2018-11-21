## How do I install it?

For manual install instructions see the [README](https://github.com/dimagi/commcare-cloud/blob/master/README.md)

### Step 1.
Make sure that you have a non-root user account on the control machine.

Let's say the user is named `admin` and the machine
is named `control.example.com`. Start by logging in as your user via SSH:

```bash
(laptop)$ ssh admin@control.example.com
```

(Did that work? Only type the text starting after the `$` in these examples.)

You should see a prompt like

```bash
admin@control.example.com:~$
```

Run this command to verify that you are in the home directory of the `admin` user.

```bash
admin@control.example.com:~$ pwd
/home/admin
```

### Step 2.

Pull commcare-cloud source code.

```bash
admin@control.example.com:~$ git clone https://github.com/dimagi/commcare-cloud.git
```

Verify that created a directory called `commcare-cloud`:

```bash
admin@control.example.com:~$ ls commcare-cloud/
commcare-cloud-bootstrap  environments  MANIFEST.in   setup.py
control                   fabfile.py    provisioning  src
dev_requirements.txt      git-hooks     README.md     tests
docs                      Makefile      scripts       Vagrantfile
```

If you see something like

```bash
ls: cannot access commcare-cloud: No such file or directory
```

then the `git clone` command did not run correctly.
Make sure you have git installed and run it again
with `--verbose` to give more logging output.

### Step 3.

Run the install script.

```bash
admin@control.example.com:~$ source commcare-cloud/control/init.sh
```

and when you see it ask you this:

```bash
Do you want to have the CommCare Cloud environment setup on login?
(y/n):
```

answer with `y`.
This will make `commcare-cloud` available to run every time you log in.

To check that commcare-cloud is now installed, run

```bash
admin@control.example.com:~$ commcare-cloud -h
usage: commcare-cloud [-h] [--control]

                      {64-test,development,echis,icds,icds-new,pna,production,softlayer,staging,swiss}
                      {bootstrap-users,ansible-playbook,django-manage,aps,tmux,ap,validate-environment-settings,deploy-stack,service,update-supervisor-confs,update-users,ping,migrate_couchdb,lookup,run-module,update-config,mosh,after-reboot,ssh,downtime,fab,update-local-known-hosts,migrate-couchdb,run-shell-command}
                      ...

```
...and then much more help output describing each possible command.

If you get to this point, congratulations! `commcare-cloud` is installed.

---

[︎⬅︎ Overview](..)
