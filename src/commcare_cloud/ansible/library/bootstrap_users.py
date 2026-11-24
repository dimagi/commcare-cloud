#! /usr/bin/python
import grp
import os
import pwd
import signal
import time
from pathlib import Path

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type

DOCUMENTATION = """
---
module: bootstrap_users

short_description: Manage dev user accounts and SSH keys.

version_added: "1.0.0"

description: Create present users, set their authorized keys, authorize
all present keys for a shared user, and remove absent users. Replaces
per-user loops over the user and authorized_key modules.

options:
    present:
        description: Mapping of username to public key text (one or more
            keys, newline-separated). Each user's authorized_keys file
            is set to exactly these keys.
        required: true
        type: dict
    absent:
        description: Usernames to remove. Their processes are killed
            before the account is deleted. Home directories are kept.
        required: false
        type: list
        elements: str
    groups:
        description: Supplementary groups for present users. Existing
            supplementary groups are replaced, like the user module
            with append=no.
        required: false
        type: list
        elements: str
    shell:
        description: Login shell for present users.
        required: false
        type: str
        default: /bin/bash
    shared_user:
        description: Existing user whose authorized_keys file is set to
            the keys of all present users.
        required: false
        type: str

author:
    - Daniel Miller (@millerdev)
"""

EXAMPLES = """
- name: Manage dev users
  bootstrap_users:
    present:
      alice: "ssh-ed25519 AAAA... alice@example.com"
    absent: [bob]
    groups: [dev]
    shared_user: ansible
"""

RETURN = """
changed:
    description: Changed flag.
    type: bool
created:
    description: Users that were created.
    type: list
updated:
    description: Users whose shell or groups were changed.
    type: list
keys_changed:
    description: Users whose authorized_keys file was changed.
    type: list
removed:
    description: Users that were removed.
    type: list
"""

KILL_TIMEOUT = 15


def main():
    module = AnsibleModule(
        argument_spec={
            'present': {'type': 'dict', 'required': True},
            'absent': {'type': 'list', 'elements': 'str', 'default': []},
            'groups': {'type': 'list', 'elements': 'str', 'default': []},
            'shell': {'type': 'str', 'default': '/bin/bash'},
            'shared_user': {'type': 'str', 'default': None},
        },
        supports_check_mode=True,
    )
    params = module.params
    present = params["present"]
    overlap = sorted(set(present) & set(params["absent"]))
    if overlap:
        module.fail_json(msg=f"Users both present and absent: {overlap}")
    users = Users(module)
    result = {
        'changed': False,
        'created': [],
        'updated': [],
        'keys_changed': [],
        'removed': [],
    }

    for name, keys in present.items():
        action = users.ensure_user(name, params["shell"], params["groups"])
        if action:
            result[action].append(name)
        if users.set_keys(name, parse_keys(keys)):
            result["keys_changed"].append(name)

    shared = params["shared_user"]
    if shared:
        all_keys = {k for keys in present.values() for k in parse_keys(keys)}
        if users.set_keys(shared, all_keys):
            result["keys_changed"].append(shared)

    for name in params["absent"]:
        if users.remove_user(name):
            result["removed"].append(name)

    result["changed"] = any(result[k] for k in [
        "created", "updated", "keys_changed", "removed"])
    module.exit_json(**result)


class Users:

    def __init__(self, module):
        self.module = module
        self.check_mode = module.check_mode

    def run(self, args):
        return self.module.run_command(args, check_rc=True)

    def ensure_user(self, name, shell, groups):
        """Create user or fix shell and groups

        Returns "created", "updated", or None.
        """
        entry = get_pwnam(name)
        if entry is None:
            if not self.check_mode:
                args = ["useradd", "--create-home", "--shell", shell]
                if groups:
                    args += ["--groups", ",".join(groups)]
                self.run(args + [name])
            return "created"
        cmd = []
        if entry.pw_shell != shell:
            cmd += ["--shell", shell]
        if sorted(get_supplementary_groups(name, entry.pw_gid)) != sorted(groups):
            cmd += ["--groups", ",".join(groups)]
        if not cmd:
            return None
        if not self.check_mode:
            self.run(["usermod"] + cmd + [name])
        return "updated"

    def set_keys(self, name, keys):
        """Set exact content of user's authorized_keys file

        Returns True if the file was (or would be) changed.
        """
        entry = get_pwnam(name)
        if entry is None:
            if self.check_mode:
                return True  # user would have been created
            self.module.fail_json(msg=f"User does not exist: {name}")
        ssh_dir = Path(entry.pw_dir) / ".ssh"
        path = ssh_dir / "authorized_keys"
        changed = False

        if not ssh_dir.is_dir():
            changed = True
            if not self.check_mode:
                ssh_dir.mkdir(mode=0o700)
        if not self.check_mode:
            changed |= self.set_owner_mode(ssh_dir, entry, 0o700)

        try:
            current = path.read_text()
        except FileNotFoundError:
            current = None
        if current is None or parse_keys(current) != keys:
            changed = True
            if not self.check_mode:
                with open(path, "w") as fh:
                    fh.write("".join(k + "\n" for k in sorted(keys)))
        if not self.check_mode:
            changed |= self.set_owner_mode(path, entry, 0o600)
        return changed

    def set_owner_mode(self, path, entry, mode):
        stat = path.stat()
        changed = False
        if (stat.st_uid, stat.st_gid) != (entry.pw_uid, entry.pw_gid):
            os.chown(path, entry.pw_uid, entry.pw_gid)
            changed = True
        if stat.st_mode & 0o7777 != mode:
            os.chmod(path, mode)
            changed = True
        return changed

    def remove_user(self, name):
        """Kill user's processes and delete the account

        Returns True if the user was (or would be) removed.
        """
        if get_pwnam(name) is None:
            return False
        if not self.check_mode:
            self.kill_processes(name)
            self.run(["userdel", name])
        return True

    def kill_processes(self, name):
        rc, out, _ = self.module.run_command(["ps", "-o", "pid=", "-u", name])
        pids = [int(p) for p in out.split()]
        for pid in pids:
            kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + KILL_TIMEOUT
        while pids and time.monotonic() < deadline:
            time.sleep(0.5)
            pids = [p for p in pids if os.path.exists(f"/proc/{p}")]
        for pid in pids:
            kill(pid, signal.SIGKILL)


def parse_keys(text):
    """Get set of keys from authorized_keys text

    Blank lines and comments are discarded.
    """
    return {
        line.strip() for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def get_pwnam(name):
    try:
        return pwd.getpwnam(name)
    except KeyError:
        return None


def get_supplementary_groups(name, primary_gid):
    return [g.gr_name for g in grp.getgrall()
            if name in g.gr_mem and g.gr_gid != primary_gid]


def kill(pid, sig):
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


if __name__ == '__main__':
    main()
